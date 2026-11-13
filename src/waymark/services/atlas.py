"""Atlases on this machine: registering them, pointing a code repo at one, references.

wm never clones, pulls or pushes. These commands only record where the
repositories already are, and read another atlas's specs where it sits.
"""

import os
from pathlib import Path

from waymark import __version__
from waymark.record import git
from waymark.record.atlas import Found, atlas_name_at, locate_atlas, locate_repo, repo_problem
from waymark.record.config import CONFIG_FILE, RECORD_DIR, Config
from waymark.record.files import RecordFiles
from waymark.record.pointer import POINTER_FILE, Pointer, render_pointer
from waymark.record.project import Project
from waymark.record.record import Record, load_record
from waymark.record.registry import Registry, load_registry, stage_registry
from waymark.record.store import Transaction
from waymark.services import integration
from waymark.services.common import Done, Refusal, commit, open_record


def _atlas_config(record: Record) -> Config:
    config = record.config
    if config is None:
        problems = [p.message for p in record.problems if p.path == CONFIG_FILE]
        detail = problems[0] if problems else "It could not be read."
        raise Refusal(f"{RECORD_DIR}/{CONFIG_FILE} has problems. {detail}")
    if config.atlas_name is None:
        raise Refusal(
            "This project keeps its record in its own repository, not in an atlas, so there is "
            "nothing to register. An atlas is made with: wm init --atlas <name>"
        )
    return config


def readable_registry() -> Registry:
    """This machine's registry, refused when it can't be read."""
    registry = load_registry()
    if registry.problems:
        raise Refusal(
            f"The registry at {registry.path} can't be read: {registry.problems[0]} "
            "Fix it, or remove it and register again."
        )
    return registry


def _commit_registry(registry: Registry) -> None:
    commit(stage_registry(registry))


def register(start: Path, repo: str | None = None, folder: str | None = None) -> Done:
    """Register the atlas around a folder and its code repos on this machine.

    Without a repo, every code repo whose path hint leads to it is registered
    too. With one, that repo is registered at the folder given.
    """
    record = open_record(start)
    config = _atlas_config(record)
    atlas = config.atlas_name
    assert atlas is not None
    root = record.project.root
    known = readable_registry()
    lines: list[str] = []
    previous = known.atlas(atlas)
    if previous and previous.path and previous.path.resolve() != root.resolve():
        lines.append(f'The atlas "{atlas}" was registered at {previous.path}; it is now here.')
    updated = known.with_atlas(atlas, root)
    lines.append(f'Registered the atlas "{atlas}" at {root}.')
    if repo is not None:
        if repo not in config.repo_names:
            listed = ", ".join(sorted(config.repo_names)) or "none yet"
            raise Refusal(
                f'The atlas "{atlas}" has no code repo "{repo}" (repos: {listed}). Add an '
                f'"[atlas.repos.{repo}]" table to {RECORD_DIR}/{CONFIG_FILE} first.'
            )
        target = (start / (folder or ".")).resolve()
        problem = repo_problem(target, atlas)
        if problem is not None:
            raise Refusal(f'"{repo}" can\'t be registered at {target}: {problem}.')
        updated = updated.with_repo(atlas, repo, target)
        lines.append(f'Registered the code repo "{repo}" at {target}.')
    else:
        for code_repo in config.repos:
            location = locate_repo(atlas, root, code_repo, updated)
            if location.found is Found.HINT and location.folder is not None:
                updated = updated.with_repo(atlas, code_repo.name, location.folder)
                lines.append(
                    f'Registered the code repo "{code_repo.name}" at {location.folder}, '
                    "found through its path hint."
                )
            elif location.found is Found.REGISTRY:
                lines.append(
                    f'The code repo "{code_repo.name}" is registered at {location.folder}.'
                )
            else:
                lines.append(f"Not found: {location.detail}")
    folders = [
        location.folder
        for code_repo in config.repos
        if (location := locate_repo(atlas, root, code_repo, updated)).folder is not None
    ]
    project_files = RecordFiles(root)
    transaction = Transaction(project_files)
    local = integration.stage_local(transaction, project_files, config.agent_tools, folders)
    _commit_registry(updated)
    commit(transaction)
    integration.keep_local(root, local)
    lines += [f"{change.status}: {change.path}" for change in local if change.status != "unchanged"]
    lines.append(f"The registry is at {updated.path}.")
    return Done("\n".join(lines))


def register_new_atlas(root: Path, name: str) -> str:
    """Register an atlas that was just created; returns what to tell the person."""
    known = load_registry()
    if known.problems:
        return f"The registry can't be read, so the atlas is not registered. {known.problems[0]}"
    _commit_registry(known.with_atlas(name, root))
    return f'Registered the atlas "{name}" on this machine.'


def _relative_hint(folder: Path, base: Path) -> str | None:
    try:
        return Path(os.path.relpath(folder, base)).as_posix()
    except ValueError:  # another drive, on Windows
        return None


def point(start: Path, atlas: str, path: str | None = None) -> Done:
    """Write the pointer file that tells a code repo which atlas holds its record."""
    top = git.repository_root(start)
    if top is None:
        raise Refusal("A pointer goes in a code repo, and this folder is not in a git repository.")
    if (top / RECORD_DIR / CONFIG_FILE).is_file():
        raise Refusal(
            f"This repository holds a Waymark record itself ({RECORD_DIR}/{CONFIG_FILE}), so it "
            "needs no pointer."
        )
    if path is not None:
        folder = (top / path).resolve()
        if atlas_name_at(folder) != atlas:
            raise Refusal(f'{folder} is not the top folder of the atlas "{atlas}".')
        hint: str | None = Path(path).as_posix()
    else:
        location = locate_atlas(atlas, load_registry())
        if location.folder is None:
            raise Refusal(f"{location.detail} Or pass its folder with --path <relative folder>.")
        folder = location.folder
        hint = _relative_hint(folder, top)
    config = load_record(Project(folder)).config
    pin = config.wm_version if config else __version__
    transaction = Transaction(RecordFiles(top))
    existed = (top / POINTER_FILE).is_file()
    transaction.write(POINTER_FILE, render_pointer(Pointer(atlas, hint, pin)))
    commit(transaction)
    verb = "Updated" if existed else "Wrote"
    return Done(
        f'{verb} {POINTER_FILE}: this repository\'s record is the atlas "{atlas}". Commit it so '
        "anyone who clones this repository finds the atlas too."
    )

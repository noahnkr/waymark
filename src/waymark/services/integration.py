"""Installing and updating the files Waymark owns in a project's agent tool folders.

The skills are rendered once to ``.agents/skills/`` and each tool's adapter
adds its own copies and settings. Files are copied, never linked. Only files
Waymark owns are written; nothing else in a tool's folder is touched.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from waymark import adapters, assets
from waymark.record import git, ignore
from waymark.record.files import RecordFiles
from waymark.record.project import RECORD_DIR
from waymark.record.record import Record
from waymark.record.store import Transaction
from waymark.services import ci, migrations
from waymark.services.common import (
    Done,
    Refusal,
    commit,
    open_record,
    repo_locations,
    require_pinned,
)

SHARED_SKILLS = ".agents/skills"
"""Where the skills are rendered once, for every tool that reads the shared folder."""


@dataclass(frozen=True)
class FileChange:
    """One file Waymark owns, and what installing did to it."""

    path: str
    status: str


def require_tools(tools: tuple[str, ...]) -> None:
    """Refuse a tool that has no adapter."""
    for tool in tools:
        if tool not in adapters.names():
            known = ", ".join(adapters.names())
            raise Refusal(
                f'"{tool}" is not an agent tool wm knows. Known tools: {known}. Fix the '
                f'"agent_tools" list in {RECORD_DIR}/config.toml.'
            )


def integration_files(files: RecordFiles, tools: tuple[str, ...]) -> dict[str, str]:
    """Every file Waymark owns for the given tools, with its full text."""
    require_tools(tools)
    rendered = {
        f"{SHARED_SKILLS}/{name}/{assets.SKILL_FILE}": assets.skill(name) for name in assets.SKILLS
    }
    for tool in tools:
        adapter = adapters.get(tool)
        existing = {
            path: files.read(path, []) if files.is_file(path) else None for path in adapter.reads
        }
        try:
            rendered.update(adapter.files(existing))
        except (ValueError, json.JSONDecodeError) as error:
            raise Refusal(
                f"{adapter.reads[0]} can't be read as settings ({error}), so wm can't add its "
                "part without risking yours. Fix the file, then run this command again."
            ) from error
    return rendered


def ignore_patterns(tools: tuple[str, ...]) -> list[str]:
    """The ``.gitignore`` patterns for the files wm writes for this machine.

    The shared skills, then each tool's files.
    """
    require_tools(tools)
    patterns = [f"/{SHARED_SKILLS}/wm-*/"]
    for tool in tools:
        patterns += adapters.get(tool).ignored
    return patterns


def stage_ignore(
    transaction: Transaction, files: RecordFiles, patterns: Sequence[str]
) -> FileChange:
    """Stage the ``.gitignore`` block for these patterns, only when it differs from the file's."""
    current = files.read(ignore.PATH, []) if files.is_file(ignore.PATH) else None
    text = ignore.merged(current, patterns)
    if text == current:
        return FileChange(ignore.PATH, "unchanged")
    transaction.write(ignore.PATH, text)
    return FileChange(ignore.PATH, "created" if current is None else "updated")


RETIRED_PREFIX = "wm-"
"""Skill folders with this prefix are wm's; one it no longer ships is removed."""


def stage_retired(
    transaction: Transaction, files: RecordFiles, tools: tuple[str, ...]
) -> list[FileChange]:
    """Stage the removal of every ``wm-*`` skill folder wm no longer ships.

    The shared skills folder and each tool's skills folder are looked at; a
    folder without the prefix is the project's own and is left alone. Each file
    removed is listed as ``removed``.
    """
    require_tools(tools)
    folders = [SHARED_SKILLS]
    for tool in tools:
        folder = adapters.get(tool).skill_folder
        if folder is not None and folder not in folders:
            folders.append(folder)
    changes: list[FileChange] = []
    for folder in folders:
        for entry in files.entries(folder):
            retired = entry.name.startswith(RETIRED_PREFIX) and entry.name not in assets.SKILLS
            if entry.is_dir and retired:
                path = f"{folder}/{entry.name}"
                transaction.delete_folder(path)
                changes += [FileChange(file, "removed") for file in files.files_under(path)]
    return changes


def stage(transaction: Transaction, files: RecordFiles, tools: tuple[str, ...]) -> list[FileChange]:
    """Stage the integration files, and say which are new, changed, current or removed."""
    changes: list[FileChange] = []
    for path, text in sorted(integration_files(files, tools).items()):
        current = files.read(path, []) if files.is_file(path) else None
        if current == text:
            changes.append(FileChange(path, "unchanged"))
        else:
            transaction.write(path, text)
            changes.append(FileChange(path, "created" if current is None else "updated"))
    return changes + stage_retired(transaction, files, tools)


def local_files(
    files: RecordFiles, tools: tuple[str, ...], folders: Sequence[Path]
) -> dict[str, str]:
    """The per-machine files that attach an atlas's code repos to each tool's sessions."""
    require_tools(tools)
    rendered: dict[str, str] = {}
    for tool in tools:
        adapter = adapters.get(tool)
        existing = {
            path: files.read(path, []) if files.is_file(path) else None
            for path in adapter.local_reads
        }
        try:
            rendered.update(adapter.local_files(existing, folders))
        except (ValueError, json.JSONDecodeError) as error:
            raise Refusal(
                f"{adapter.local_reads[0]} can't be read as settings ({error}), so wm can't "
                "attach the code repos without risking yours. Fix the file, then run this "
                "command again."
            ) from error
    return rendered


def stage_local(
    transaction: Transaction, files: RecordFiles, tools: tuple[str, ...], folders: Sequence[Path]
) -> list[FileChange]:
    """Stage the per-machine files, and say which are new, changed or already current."""
    changes: list[FileChange] = []
    for path, text in sorted(local_files(files, tools, folders).items()):
        current = files.read(path, []) if files.is_file(path) else None
        if current == text:
            changes.append(FileChange(path, "unchanged"))
        else:
            transaction.write(path, text)
            changes.append(FileChange(path, "created" if current is None else "updated"))
    return changes


def keep_local(root: Path, changes: Sequence[FileChange]) -> None:
    """Keep per-machine files out of the project's commits, through the clone's exclude file."""
    for change in changes:
        if not git.is_ignored(root, change.path):
            git.exclude(root, change.path)


def located_folders(record: Record) -> list[Path]:
    """The folders of the atlas's code repos found on this machine, in settings order."""
    return [
        location.folder
        for location in repo_locations(record).values()
        if location.folder is not None
    ]


@dataclass(frozen=True)
class MachineSetup:
    """What setting up this machine did: the files it wrote."""

    changes: list[FileChange]
    paths: tuple[str, ...]


def setup_machine(record: Record) -> MachineSetup:
    """Write the files wm keeps for this machine, and keep them out of git.

    The agent tool files, the per-machine files and the ``.gitignore`` block are
    written in one transaction; the per-machine files are then excluded in this
    clone. The record itself is not touched, and no git setting is changed.
    """
    assert record.config is not None
    root = record.project.root
    tools = record.config.agent_tools
    files = RecordFiles(root)
    transaction = Transaction(files)
    changes = stage(transaction, files, tools)
    local = stage_local(transaction, files, tools, located_folders(record))
    gitignore = stage_ignore(transaction, files, ignore_patterns(tools))
    paths = commit(transaction)
    keep_local(root, local)
    return MachineSetup([*changes, *local, gitignore], paths)


def _listed(items: Sequence[str]) -> str:
    """Items joined for a sentence: "a", "a and b", "a, b and c"."""
    *rest, last = items
    return f"{', '.join(rest)} and {last}" if rest else last


def update(start: Path) -> Done:
    """Migrate the record to this version's format and regenerate the files Waymark owns.

    The last line asks for a review and a commit only when something shared
    changed: the record, ``.gitignore`` or the CI workflow. The files that
    belong to this machine are never to be committed.
    """
    record = open_record(start)
    require_pinned(record)
    migrated = migrations.migrate(record.files)
    record = open_record(start, writing=True)
    project_files = RecordFiles(record.project.root)
    transaction = Transaction(project_files)
    workflow = ci.stage_workflow(transaction, project_files, only_if_present=True)
    paths = commit(transaction)
    machine = setup_machine(record)
    changes = list(machine.changes)
    if workflow != "absent":
        changes.append(FileChange(ci.WORKFLOW, workflow))
    changed = [change for change in changes if change.status != "unchanged"]
    lines = [f"Migrated the record: {step}." for step in migrated]
    lines += [f"{change.status}: {change.path}" for change in changed]
    shared = [f"{RECORD_DIR}/"] if migrated else []
    shared += [change.path for change in changed if change.path in (ignore.PATH, ci.WORKFLOW)]
    if shared:
        lines.append(f"Review the changes to {_listed(shared)} and commit them.")
    elif changed:
        lines.append("Updated this machine's files.")
    else:
        lines.append("Everything is up to date.")
    return Done("\n".join(lines), paths + machine.paths)

"""Checking the setup on this machine. Nothing here changes anything.

``doctor`` checks wm itself, git, the project and its agent tool files.
``atlas_doctor`` checks an atlas's registry entries, code repos, branches and
pins.
"""

import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waymark import __version__
from waymark.record import git
from waymark.record.atlas import Found, locate_atlas, locate_repo, read_pointer
from waymark.record.config import CONFIG_FILE, RECORD_DIR, RECORD_FORMAT
from waymark.record.files import RecordFiles
from waymark.record.pointer import POINTER_FILE
from waymark.record.project import Project, ProjectNotFoundError, find_project
from waymark.record.record import Record, load_record
from waymark.record.registry import Registry, load_registry
from waymark.services import integration
from waymark.services.common import Refusal, install_hint


class Status(StrEnum):
    """How one check came out. Only errors make the doctor fail."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Check:
    """One check: what it looked at, how it came out, and what to do.

    ``folder`` is the place on this machine the check is about, if any.
    """

    name: str
    status: Status
    message: str
    folder: Path | None = None


@dataclass(frozen=True)
class Report:
    """What a doctor found."""

    scope: str
    checks: tuple[Check, ...]

    @property
    def failed(self) -> bool:
        return any(check.status is Status.ERROR for check in self.checks)


def _wm_on_path() -> Check:
    found = shutil.which("wm")
    if found is None:
        return Check(
            "wm on PATH",
            Status.ERROR,
            "wm is not on PATH, so agent tool hooks and git hooks can't run it. Install it as "
            f"a tool: {install_hint(__version__)}",
        )
    return Check("wm on PATH", Status.OK, f"wm {__version__} is installed.", Path(found))


def _git() -> Check:
    line = git.version()
    if line is None:
        return Check("git", Status.ERROR, "git can't be run. Install it and put it on PATH.")
    return Check("git", Status.OK, line)


def _project_check(project: Project) -> Check:
    if project.code_repo is not None:
        return Check(
            "project",
            Status.OK,
            "Found the atlas from the code repo this command ran in.",
            project.root,
        )
    return Check("project", Status.OK, "Found the record.", project.root)


def _pin_checks(record: Record) -> list[Check]:
    config = record.config
    if config is None:
        problems = [p.message for p in record.problems if p.path == CONFIG_FILE]
        detail = problems[0] if problems else "It could not be read."
        return [Check("settings", Status.ERROR, f"{RECORD_DIR}/{CONFIG_FILE}: {detail}")]
    checks: list[Check] = []
    if config.wm_version != __version__:
        checks.append(
            Check(
                "version pin",
                Status.ERROR,
                f"The project is pinned to wm {config.wm_version}, and this is wm {__version__}. "
                f"Reading works; writing is refused. Install the pinned version: "
                f"{install_hint(config.wm_version)}",
            )
        )
        return checks
    checks.append(Check("version pin", Status.OK, f"Pinned to wm {config.wm_version}."))
    if config.record_format != RECORD_FORMAT:
        checks.append(
            Check(
                "record format",
                Status.WARNING,
                f"The record is in format {config.record_format}; this wm writes format "
                f'{RECORD_FORMAT}. Run "wm update" to migrate it.',
            )
        )
        return checks
    checks.append(Check("record format", Status.OK, f"Format {config.record_format}."))
    checks.append(_tool_files(record))
    return checks


def _tool_files(record: Record) -> Check:
    assert record.config is not None
    files = RecordFiles(record.project.root)
    try:
        wanted = integration.integration_files(files, record.config.agent_tools)
    except Refusal as refusal:
        return Check("agent tool files", Status.ERROR, str(refusal))
    stale = sorted(
        path
        for path, text in wanted.items()
        if (files.read(path, []) if files.is_file(path) else None) != text
    )
    if stale:
        return Check(
            "agent tool files",
            Status.WARNING,
            f"{len(stale)} file(s) Waymark owns are missing or out of date, starting with "
            f'{stale[0]}. Run "wm update", then review and commit the changes.',
        )
    return Check("agent tool files", Status.OK, "The skills, agents and hooks are current.")


def _reference_checks(record: Record, registry: Registry) -> list[Check]:
    checks: list[Check] = []
    for reference in record.config.references if record.config else ():
        location = locate_atlas(reference.atlas, registry, record.project.root, reference.path_hint)
        name = f"reference {reference.atlas}"
        if location.found is Found.MISSING:
            checks.append(Check(name, Status.WARNING, location.detail))
        elif location.found is Found.HINT:
            checks.append(Check(name, Status.WARNING, location.detail, location.folder))
        else:
            checks.append(Check(name, Status.OK, "Registered.", location.folder))
    return checks


def doctor(start: Path) -> Report:
    """Check wm, git and the project around a folder."""
    checks = [_wm_on_path(), _git()]
    registry = load_registry()
    if registry.problems:
        checks.append(Check("registry", Status.ERROR, registry.problems[0], registry.path))
    try:
        project = find_project(start, registry)
    except ProjectNotFoundError as error:
        checks.append(Check("project", Status.ERROR, error.plain, start))
        return Report("project", tuple(checks))
    checks.append(_project_check(project))
    record = load_record(project)
    checks += _pin_checks(record)
    checks += _reference_checks(record, registry)
    if record.config is not None and record.config.atlas_name is not None:
        checks.append(
            Check("atlas", Status.OK, 'This is an atlas. "wm atlas doctor" checks its code repos.')
        )
    return Report("project", tuple(checks))


def _registry_checks(atlas: str, root: Path, registry: Registry) -> list[Check]:
    if registry.problems:
        return [Check("registry", Status.ERROR, registry.problems[0], registry.path)]
    checks = [Check("registry", Status.OK, "The registry can be read.", registry.path)]
    entry = registry.atlas(atlas)
    if entry is None or entry.path is None:
        checks.append(
            Check(
                "atlas registered",
                Status.WARNING,
                f'The atlas "{atlas}" is not registered on this machine. Run "wm atlas register" '
                "in it.",
            )
        )
    elif entry.path.resolve() != root.resolve():
        checks.append(
            Check(
                "atlas registered",
                Status.WARNING,
                f'The registry has the atlas "{atlas}" at another folder, shown below. Run '
                '"wm atlas register" here if this is the one to use.',
                entry.path,
            )
        )
    else:
        checks.append(Check("atlas registered", Status.OK, f'"{atlas}" is registered.', root))
    return checks


def _pointer_check(name: str, folder: Path, atlas: str, pin: str) -> Check | None:
    pointer, problem = read_pointer(folder)
    if problem is not None:
        return Check(f"pointer {name}", Status.ERROR, problem, folder)
    if pointer is None:
        return None
    if pointer.wm_version not in (None, pin):
        return Check(
            f"pointer {name}",
            Status.WARNING,
            f"Its {POINTER_FILE} pins wm {pointer.wm_version}; the atlas pins {pin}. Run "
            f'"wm atlas point {atlas}" in it to bring the pointer up to date.',
            folder,
        )
    return Check(f"pointer {name}", Status.OK, f'{POINTER_FILE} names "{atlas}".', folder)


def _repo_checks(record: Record, registry: Registry) -> list[Check]:
    config = record.config
    assert config is not None
    assert config.atlas_name is not None
    atlas, root = config.atlas_name, record.project.root
    checks: list[Check] = []
    for repo in config.repos:
        location = locate_repo(atlas, root, repo, registry)
        name = f"repo {repo.name}"
        if location.folder is None:
            checks.append(Check(name, Status.WARNING, location.detail))
            continue
        branch = git.current_branch(location.folder)
        where = f"on branch {branch}" if branch else "with no branch checked out"
        status = Status.OK if location.found is Found.REGISTRY else Status.WARNING
        message = f"Found, {where}." + (f" {location.detail}" if location.detail else "")
        checks.append(Check(name, status, message, location.folder))
        pointer = _pointer_check(repo.name, location.folder, atlas, config.wm_version)
        if pointer is not None:
            checks.append(pointer)
    entry = registry.atlas(atlas)
    for leftover in sorted(set(entry.repos) - config.repo_names) if entry else ():
        checks.append(
            Check(
                f"repo {leftover}",
                Status.WARNING,
                f'The registry has a code repo "{leftover}" that the atlas\'s settings no longer '
                "list. It does no harm; remove it from the registry file if it is gone for good.",
            )
        )
    return checks


def _local_files_check(record: Record, registry: Registry) -> Check:
    config = record.config
    assert config is not None
    assert config.atlas_name is not None
    folders = [
        location.folder
        for repo in config.repos
        if (location := locate_repo(config.atlas_name, record.project.root, repo, registry)).folder
        is not None
    ]
    files = RecordFiles(record.project.root)
    try:
        wanted = integration.local_files(files, config.agent_tools, folders)
    except Refusal as refusal:
        return Check("attached repos", Status.ERROR, str(refusal))
    stale = sorted(
        path
        for path, text in wanted.items()
        if (files.read(path, []) if files.is_file(path) else None) != text
    )
    if stale:
        return Check(
            "attached repos",
            Status.WARNING,
            f"{stale[0]} doesn't attach every code repo found on this machine to the agent "
            'tool\'s sessions. Run "wm atlas register" to attach them.',
        )
    return Check("attached repos", Status.OK, "The code repos found are attached to sessions.")


def atlas_doctor(start: Path) -> Report:
    """Check an atlas's setup on this machine: registry, paths, branches and pins."""
    registry = load_registry()
    try:
        project = find_project(start, registry)
    except ProjectNotFoundError as error:
        return Report("atlas", (Check("project", Status.ERROR, error.plain, start),))
    record = load_record(project)
    config = record.config
    if config is None or config.atlas_name is None:
        message = (
            "This project keeps its record in its own repository; it is not an atlas."
            if config is not None
            else f"{RECORD_DIR}/{CONFIG_FILE} can't be read; run wm check."
        )
        return Report("atlas", (Check("atlas", Status.ERROR, message, project.root),))
    checks = [Check("atlas", Status.OK, f'The atlas "{config.atlas_name}".', project.root)]
    checks += _registry_checks(config.atlas_name, project.root, registry)
    if config.wm_version != __version__:
        checks.append(
            Check(
                "version pin",
                Status.ERROR,
                f"The atlas pins wm {config.wm_version}, and this is wm {__version__}. "
                f"Install the pinned version: {install_hint(config.wm_version)}",
            )
        )
    else:
        checks.append(Check("version pin", Status.OK, f"Pinned to wm {config.wm_version}."))
    branch = git.current_branch(project.root)
    checks.append(
        Check(
            "atlas branch",
            Status.OK if branch else Status.WARNING,
            f"On branch {branch}." if branch else "No branch is checked out in the atlas.",
            project.root,
        )
    )
    if not registry.problems:
        checks += _repo_checks(record, registry)
        checks.append(_local_files_check(record, registry))
    return Report("atlas", tuple(checks))

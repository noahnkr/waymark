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
from waymark.record import git
from waymark.record.files import RecordFiles
from waymark.record.project import RECORD_DIR
from waymark.record.record import Record
from waymark.record.store import Transaction
from waymark.services import ci, githooks, migrations
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


def stage(transaction: Transaction, files: RecordFiles, tools: tuple[str, ...]) -> list[FileChange]:
    """Stage the integration files, and say which are new, changed or already current."""
    changes: list[FileChange] = []
    for path, text in sorted(integration_files(files, tools).items()):
        current = files.read(path, []) if files.is_file(path) else None
        if current == text:
            changes.append(FileChange(path, "unchanged"))
        else:
            transaction.write(path, text)
            changes.append(FileChange(path, "created" if current is None else "updated"))
    return changes


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


def update(start: Path) -> Done:
    """Migrate the record to this version's format and regenerate the files Waymark owns."""
    record = open_record(start)
    require_pinned(record)
    migrated = migrations.migrate(record.files)
    record = open_record(start, writing=True)
    assert record.config is not None
    project_files = RecordFiles(record.project.root)
    transaction = Transaction(project_files)
    changes = stage(transaction, project_files, record.config.agent_tools)
    local = stage_local(
        transaction, project_files, record.config.agent_tools, located_folders(record)
    )
    workflow = ci.stage_workflow(transaction, project_files, only_if_present=True)
    commit(transaction)
    keep_local(record.project.root, local)
    changes += local
    if workflow != "absent":
        changes.append(FileChange(ci.WORKFLOW, workflow))
    hooks = githooks.install(record.project.root)
    lines = [f"Migrated the record: {step}." for step in migrated]
    lines += [
        f"{change.status}: {change.path}" for change in changes if change.status != "unchanged"
    ]
    lines += hooks
    untouched = sum(1 for change in changes if change.status == "unchanged")
    if not migrated and not hooks and untouched == len(changes):
        lines.append("Everything is up to date.")
    else:
        lines.append(f"{untouched} file(s) already current. Review the changes and commit them.")
    return Done("\n".join(lines), transaction.paths)

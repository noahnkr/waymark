"""Installing and updating the files Waymark owns in a project's agent tool folders.

The skills are rendered once to ``.agents/skills/`` and each tool's adapter
adds its own copies and settings. Files are copied, never linked. Only files
Waymark owns are written; nothing else in a tool's folder is touched.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from waymark import adapters, assets
from waymark.record.files import RecordFiles
from waymark.record.project import RECORD_DIR
from waymark.record.store import Transaction
from waymark.services import migrations
from waymark.services.common import Done, Refusal, commit, open_record, require_pinned

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
    commit(transaction)
    lines = [f"Migrated the record: {step}." for step in migrated]
    lines += [
        f"{change.status}: {change.path}" for change in changes if change.status != "unchanged"
    ]
    untouched = sum(1 for change in changes if change.status == "unchanged")
    if not migrated and untouched == len(changes):
        lines.append("Everything is up to date.")
    else:
        lines.append(f"{untouched} file(s) already current. Review the changes and commit them.")
    return Done("\n".join(lines), transaction.paths)

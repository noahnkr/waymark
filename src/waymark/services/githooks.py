"""The git hooks: installing them, and the two checks they run.

``commit-msg`` checks the message's conventional-commit format, with the
project's scopes when it lists any. ``pre-commit`` runs the health check when
the commit changes the record. Both are installed into ``.waymark/hooks/``
and run through ``core.hooksPath``; a repository with another hook manager is
told what to add instead.
"""

import datetime
from pathlib import Path

from waymark.record import git, ignore
from waymark.record.commits import commit_problem
from waymark.record.config import CONFIG_FILE, RECORD_DIR, parse_config
from waymark.record.files import RecordFiles
from waymark.record.githooks import (
    HOOKS,
    HOOKS_DIR,
    HOOKS_IGNORED,
    hook_files,
    hook_manager,
    make_executable,
    read_message,
)
from waymark.record.project import Project, ProjectNotFoundError, find_project
from waymark.record.record import load_record
from waymark.record.store import Transaction
from waymark.services.check import Severity, check_record
from waymark.services.common import Done, Refusal, commit

COMMANDS = {
    "commit-msg": 'wm run-hook commit-msg "$1"',
    "pre-commit": "wm run-hook pre-commit",
}
"""What each hook runs, for a hook manager to call."""

_SHOWN = 5


def install(root: Path, *, record: bool) -> list[str]:
    """Write the hooks into a repository and point this clone's git at them.

    The hooks belong to each clone: nothing is staged. In a repository without
    a record (``record`` is False), the ``.gitignore`` block that keeps the hooks
    out of git is written here; with a record, the caller writes the full block.
    A repository that already uses another hook setup is not taken over; the
    lines say what to add to it instead.
    """
    manager = hook_manager(root)
    if manager is not None:
        manual = [f"Git hooks: not installed, because {manager}. Add these to it instead:"]
        return manual + [f"  {name}: {command}" for name, command in COMMANDS.items()]
    files = RecordFiles(root)
    transaction = Transaction(files)
    lines: list[str] = []
    for path, text in sorted(hook_files().items()):
        current = files.read(path, []) if files.is_file(path) else None
        if current != text:
            transaction.write(path, text)
            lines.append(f"{'created' if current is None else 'updated'}: {path}")
    if not record:
        current = files.read(ignore.PATH, []) if files.is_file(ignore.PATH) else None
        text = ignore.merged(current, [HOOKS_IGNORED])
        if text != current:
            transaction.write(ignore.PATH, text)
            lines.append(f"{'created' if current is None else 'updated'}: {ignore.PATH}")
    commit(transaction)
    make_executable(root)
    if git.config_value(root, "core.hooksPath") != HOOKS_DIR:
        git.set_config(root, "core.hooksPath", HOOKS_DIR)
        lines.append(f"Git in this clone now runs the hooks in {HOOKS_DIR}/ (core.hooksPath).")
    return lines


def _scopes(start: Path) -> tuple[str, ...] | None:
    """The project's commit scopes, if it lists any; None means any scope is accepted."""
    try:
        project = find_project(start)
    except ProjectNotFoundError:
        return None
    text = RecordFiles(project.record_root).read(CONFIG_FILE, [])
    config = parse_config(text)[0] if text is not None else None
    return config.commit_scopes if config else None


def check_commit_message(start: Path, message_file: str) -> Done:
    """The commit-msg hook: refuse a message that isn't a conventional commit."""
    path = Path(message_file)
    message = read_message(path if path.is_absolute() else start / path)
    problem = commit_problem(message, _scopes(start))
    if problem is not None:
        raise Refusal(f"The commit was stopped: {problem}")
    return Done("")


def check_staged_record(start: Path, now: datetime.datetime) -> Done:
    """The pre-commit hook: when the commit changes the record, refuse it while wm check fails.

    The record's files are checked as they are on disk.
    """
    root = git.repository_root(start)
    if root is None or not (root / RECORD_DIR / CONFIG_FILE).is_file():
        return Done("")
    staged = git.staged_paths(root)
    if not any(path.startswith(f"{RECORD_DIR}/") for path in staged):
        return Done("")
    findings = check_record(load_record(Project(root)), now)
    errors = [finding for finding in findings if finding.severity is Severity.ERROR]
    if not errors:
        return Done("")
    lines = [
        f"- {RECORD_DIR}/{e.path}{f':{e.line}' if e.line else ''}: {e.message}"
        for e in errors[:_SHOWN]
    ]
    more = f"\n... and {len(errors) - _SHOWN} more." if len(errors) > _SHOWN else ""
    raise Refusal(
        f"The commit was stopped: it changes the record, and wm check finds {len(errors)} "
        "error(s):\n" + "\n".join(lines) + more + '\nFix them, then commit again; "wm check" '
        "lists them all."
    )


HOOK_NAMES = tuple(HOOKS)

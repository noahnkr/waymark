"""The health check: everything wrong with the record, and everything worth a look."""

import datetime
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waymark import __version__
from waymark.record import git
from waymark.record.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.problems import WHOLE_FILE
from waymark.record.project import RECORD_DIR
from waymark.record.record import Record, link_problems
from waymark.record.state import ConflictKind, ExplorationStatus, RecordState, derive_state
from waymark.record.terms import ReviewLevel
from waymark.services.common import install_hint, open_record

STALE_AFTER_DAYS = 30
"""A change untouched in git for this long is worth a look."""


class Severity(StrEnum):
    """Errors make the check fail; warnings are reported and pass."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, order=True)
class Finding:
    """One thing the check found. ``path`` is relative to the record's root."""

    severity: Severity
    path: str
    line: int
    code: str
    message: str


def _state_findings(record: Record, state: RecordState) -> list[Finding]:
    found: list[Finding] = []
    for name, change in state.changes.items():
        path = record.changes[name].path
        found.extend(
            Finding(Severity.ERROR, path, WHOLE_FILE, "conflict", conflict.message)
            for conflict in change.conflicts
            if conflict.kind is ConflictKind.MISMATCH
        )
        if change.applied:
            message = (
                f'The change "{name}" is applied but not archived. The human archives it on '
                f'its branch with "wm archive {name}", before its pull request.'
            )
            found.append(Finding(Severity.WARNING, path, WHOLE_FILE, "not-archived", message))
        found.extend(_review_level_findings(record, name))
    found.extend(
        Finding(Severity.WARNING, "changes", WHOLE_FILE, "overlap", conflict.message)
        for conflict in state.overlaps
    )
    for name, exploration in state.explorations.items():
        if exploration.status is ExplorationStatus.UNREADABLE:
            path = record.explorations[name].doc.path
            found.append(
                Finding(
                    Severity.ERROR,
                    path,
                    WHOLE_FILE,
                    "conclusion-unreadable",
                    exploration.detail or "",
                )
            )
    return found


def _review_level_findings(record: Record, name: str) -> list[Finding]:
    """A change that modifies or removes a requirement should be reviewed independently."""
    change = record.changes[name]
    level = change.review_level(record.default_review)
    risky = any(delta.modified or delta.removed for delta in change.deltas.values())
    if not risky or level is ReviewLevel.INDEPENDENT or change.proposal is None:
        return []
    message = (
        f'The change "{name}" modifies or removes a requirement, and its review level is '
        f'{level}. A change like this should be reviewed independently: add a "Review: '
        'independent" line to its proposal.'
    )
    return [
        Finding(Severity.WARNING, change.proposal.doc.path, WHOLE_FILE, "review-level", message)
    ]


def _stale_findings(record: Record, now: datetime.datetime) -> list[Finding]:
    root = record.project.root
    folders = {f"{RECORD_DIR}/{change.path}": change for change in record.changes.values()}
    found: list[Finding] = []
    for folder, when in git.last_changed(root, folders).items():
        days = (now - when).days
        if days >= STALE_AFTER_DAYS:
            change = folders[folder]
            message = (
                f'The change "{change.name}" has not been touched for {days} days. '
                "Pick it up again, or remove it if it was dropped."
            )
            found.append(Finding(Severity.WARNING, change.path, WHOLE_FILE, "stale", message))
    return found


def _setup_findings(record: Record) -> list[Finding]:
    config = record.config
    found: list[Finding] = []
    if config is None:
        return found
    if config.wm_version != __version__:
        message = (
            f"The project is pinned to wm {config.wm_version}, and this is wm {__version__}. "
            f"Writing commands are refused. Install the pinned version: "
            f"{install_hint(config.wm_version)}"
        )
        found.append(Finding(Severity.WARNING, CONFIG_FILE, WHOLE_FILE, "version-pin", message))
    if config.record_format != RECORD_FORMAT:
        message = (
            f"The record is in format {config.record_format}, and this wm writes format "
            f'{RECORD_FORMAT}. Run "wm update" to migrate it.'
        )
        found.append(Finding(Severity.WARNING, CONFIG_FILE, WHOLE_FILE, "record-format", message))
    return found


def check_record(record: Record, now: datetime.datetime) -> tuple[Finding, ...]:
    """Everything the health check finds in a loaded record, in a stable order."""
    found = [
        Finding(Severity.ERROR, p.path, p.line, p.code, p.message)
        for p in (*record.problems, *link_problems(record))
    ]
    found += _state_findings(record, derive_state(record))
    found += _stale_findings(record, now)
    found += _setup_findings(record)
    return tuple(sorted(found))


def check(start: Path, now: datetime.datetime) -> tuple[Finding, ...]:
    """Check the record around a folder. Reading never needs the pinned version."""
    return check_record(open_record(start), now)


def has_errors(findings: tuple[Finding, ...]) -> bool:
    """Whether the check fails."""
    return any(finding.severity is Severity.ERROR for finding in findings)

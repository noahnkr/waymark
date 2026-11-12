"""The data behind every view: plain payloads built from the record and its state.

A payload holds only JSON types. It carries its schema's name and version, and
nothing that differs between machines on the same commit.
"""

import datetime
from typing import Any

from waymark import __version__
from waymark.record.changes import Change
from waymark.record.config import RECORD_FORMAT
from waymark.record.explorations import QUESTIONS, Exploration
from waymark.record.milestones import Milestone
from waymark.record.record import (
    ArchiveEntry,
    Record,
    load_archived_change,
    spec_history,
)
from waymark.record.specs import Spec
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    Conflict,
    ConflictKind,
    ExplorationStatus,
    RecordState,
    StepKind,
    change_state,
    derive_state,
    exploration_state,
    milestone_state,
    overlaps,
)
from waymark.record.tasks import Item
from waymark.record.terms import Verdict
from waymark.services.check import Finding, Severity, check_record
from waymark.services.common import Refusal

Payload = dict[str, Any]

VERSIONS = {
    "status": 1,
    "inbox": 1,
    "ls": 1,
    "check": 1,
    "show.change": 1,
    "show.spec": 1,
    "show.milestone": 1,
    "show.exploration": 1,
}
"""The schema version of each payload. A breaking change to a payload bumps its number."""

KINDS = ("change", "spec", "milestone", "exploration")
RECENT = 5


def _header(name: str) -> Payload:
    return {"schema": f"wm.{name}", "version": VERSIONS[name]}


def _conflict(conflict: Conflict) -> Payload:
    return {
        "kind": conflict.kind.value,
        "spec": conflict.domain,
        "requirement": conflict.requirement,
        "changes": list(conflict.changes),
        "message": conflict.message,
    }


def _change_summary(state: ChangeState) -> Payload:
    step = state.next_step
    return {
        "name": state.name,
        "owner": state.owner,
        "phase": state.phase.value,
        "short_path": state.short_path,
        "acceptance": state.acceptance.value,
        "ticked": state.ticked,
        "total": state.total,
        "next_step": {
            "kind": step.kind.value,
            "item": step.item,
            "human": step.human,
            "reason": step.reason,
        },
        "conflicts": [_conflict(conflict) for conflict in state.conflicts],
    }


def _entry(kind: str, summary: str, **fields: str | None) -> Payload:
    base: Payload = {"kind": kind, "change": None, "item": None, "exploration": None}
    return {**base, **fields, "summary": summary}


def _item_entries(name: str, change: Change, state: ChangeState) -> list[Payload]:
    entries: list[Payload] = []
    items = {item.number: item for item in (change.tasks.items if change.tasks else ())}
    command = f'wm resolve {name} {{}} "<what was decided>"'
    for item_state in state.items:
        item = items[item_state.number]
        last = item.records[-1] if item.records else None
        number = item.number
        if item_state.escalated:
            gap = item.spec_gap is not None or (last and last.verdict is Verdict.SPEC_GAP)
            entries.append(
                _entry(
                    "spec-gap" if gap else "verdict",
                    item_state.escalated,
                    change=name,
                    item=number,
                    command=command.format(number),
                )
            )
        elif item.blocked and not item.ticked:
            entries.append(
                _entry(
                    "blocked",
                    item.blocked,
                    change=name,
                    item=number,
                    command=command.format(number),
                )
            )
    return entries


_INBOX_ORDER = ("accept", "spec-gap", "verdict", "blocked", "conflict", "archive", "question")


def inbox_entries(record: Record, state: RecordState) -> list[Payload]:
    """Everything only the human can resolve, most pressing kind first."""
    entries: list[Payload] = []
    for name in sorted(state.changes):
        change_state_ = state.changes[name]
        step = change_state_.next_step
        if step.kind is StepKind.ACCEPT:
            again = change_state_.acceptance is AcceptanceState.WITHDRAWN
            summary = f"Accept again: {step.reason}" if again else "Ready to accept."
            entries.append(_entry("accept", summary, change=name, command=f"wm accept {name}"))
        if step.kind is StepKind.ARCHIVE:
            command = f'wm archive {name} --outcome "<what came of it>"'
            entries.append(
                _entry("archive", "Applied; ready to archive.", change=name, command=command)
            )
        entries.extend(
            _entry("conflict", conflict.message, change=name, command=None)
            for conflict in change_state_.conflicts
            if conflict.kind is ConflictKind.MISMATCH
        )
        entries.extend(_item_entries(name, record.changes[name], change_state_))
    for name in sorted(state.explorations):
        questions = record.explorations[name].sections[QUESTIONS]
        if state.explorations[name].status is ExplorationStatus.OPEN and questions:
            entries.append(_entry("question", questions, exploration=name, command=None))
    return sorted(entries, key=lambda entry: _INBOX_ORDER.index(entry["kind"]))


def _writable(record: Record) -> bool:
    config = record.config
    return (
        config is not None
        and config.wm_version == __version__
        and config.record_format == RECORD_FORMAT
    )


def status(record: Record) -> Payload:
    """Where things stand: changes in flight, milestones, what needs the human."""
    state = derive_state(record)
    config = record.config
    milestones = []
    for name in sorted(state.milestones):
        milestone = state.milestones[name]
        planned = len(milestone.lines) - milestone.total
        milestones.append(
            {
                "name": name,
                "archived": milestone.archived,
                "total": milestone.total,
                "planned": planned,
            }
        )
    recent = sorted(record.archived_changes, reverse=True)[:RECENT]
    return {
        **_header("status"),
        "layout": record.layout.value,
        "atlas": config.atlas_name if config else None,
        "wm_version": __version__,
        "pinned_version": config.wm_version if config else None,
        "writable": _writable(record),
        "changes": [_change_summary(state.changes[name]) for name in sorted(state.changes)],
        "milestones": milestones,
        "needs_human": len(inbox_entries(record, state)),
        "recently_archived": [
            {"name": entry.name, "date": entry.date.isoformat()} for entry in recent
        ],
        "problems": len(record.problems),
    }


def inbox(record: Record) -> Payload:
    """What only the human can resolve."""
    return {**_header("inbox"), "entries": inbox_entries(record, derive_state(record))}


def _finding(finding: Finding) -> Payload:
    return {
        "severity": finding.severity.value,
        "path": finding.path,
        "line": finding.line,
        "code": finding.code,
        "message": finding.message,
    }


def check(record: Record, now: datetime.datetime) -> Payload:
    """The health check's findings."""
    findings = check_record(record, now)
    errors = sum(1 for finding in findings if finding.severity is Severity.ERROR)
    return {
        **_header("check"),
        "findings": [_finding(finding) for finding in findings],
        "errors": errors,
        "warnings": len(findings) - errors,
    }


def _ls_changes(record: Record, state: RecordState, archived: bool) -> list[Payload]:
    entries = []
    for name in sorted(state.changes):
        change = state.changes[name]
        detail = f"{change.ticked}/{change.total} items; next: {change.next_step.kind.value}"
        entries.append({"name": name, "state": change.phase.value, "detail": detail})
    if archived:
        entries.extend(
            {"name": entry.name, "state": "archived", "detail": entry.date.isoformat()}
            for entry in sorted(record.archived_changes, reverse=True)
        )
    return entries


def _ls_specs(record: Record) -> list[Payload]:
    entries = []
    for name in sorted(record.specs):
        pending = sum(1 for change in record.changes.values() if name in change.deltas)
        count = len(record.specs[name].requirements)
        detail = f"{count} requirement{'s' if count != 1 else ''}"
        if pending:
            detail += f"; {pending} pending change{'s' if pending != 1 else ''}"
        entries.append({"name": name, "state": "living", "detail": detail})
    return entries


def ls(record: Record, kind: str, *, archived: bool = False) -> Payload:
    """One entry per change, spec, milestone or exploration, with its state."""
    state = derive_state(record)
    entries: list[Payload]
    if kind == "change":
        entries = _ls_changes(record, state, archived)
    elif kind == "spec":
        entries = _ls_specs(record)
    elif kind == "milestone":
        entries = [
            {
                "name": name,
                "state": "open",
                "detail": f"{milestone.archived}/{milestone.total} changes archived",
            }
            for name, milestone in sorted(state.milestones.items())
        ]
        if archived:
            entries.extend(
                {"name": entry.name, "state": "closed", "detail": entry.date.isoformat()}
                for entry in sorted(record.archived_milestones, reverse=True)
            )
    else:
        entries = [
            {"name": name, "state": exploration.status.value, "detail": exploration.detail or ""}
            for name, exploration in sorted(state.explorations.items())
        ]
    return {**_header("ls"), "kind": kind, "entries": entries}


def _item(item: Item, state: ChangeState | None) -> Payload:
    item_state = next((i for i in state.items if i.number == item.number), None) if state else None
    return {
        "number": item.number,
        "title": item.title,
        "ticked": item.ticked,
        "level": item_state.level.value if item_state else None,
        "reviewed": item_state.reviewed if item_state else None,
        "needs_human": item_state.escalated if item_state else None,
        "criteria": item.criteria,
        "verify": item.verify,
        "repo": item.repo,
        "blocked": item.blocked,
        "spec_gap": item.spec_gap,
        "notes": list(item.notes),
        "records": [
            {
                "kind": record.kind.value,
                "date": record.date.isoformat(),
                "verdict": record.verdict.value if record.verdict else None,
                "text": record.text,
            }
            for record in item.records
        ],
    }


def show_change(record: Record, change: Change) -> Payload:
    """Everything about one change, active or archived."""
    active = change.archived_on is None
    state = change_state(record, change, overlaps(record)) if active else None
    proposal = change.proposal
    return {
        **_header("show.change"),
        "name": change.name,
        "path": change.path,
        "archived_on": change.archived_on.isoformat() if change.archived_on else None,
        "title": proposal.title if proposal else None,
        "state": _change_summary(state) if state else None,
        "owner": proposal.owner if proposal else None,
        "accepted": (
            {"date": proposal.acceptance.date.isoformat(), "by": proposal.acceptance.who}
            if proposal and proposal.acceptance
            else None
        ),
        "synced_on": proposal.synced.isoformat() if proposal and proposal.synced else None,
        "proposal": dict(proposal.sections) if proposal else None,
        "outcome": proposal.outcome if proposal else None,
        "deltas": [
            {
                "spec": domain,
                "added": [item.name for item in delta.added],
                "modified": [item.name for item in delta.modified],
                "removed": [item.name for item in delta.removed],
            }
            for domain, delta in sorted(change.deltas.items())
        ],
        "design": (
            {"decisions": [decision.name for decision in change.design.decisions]}
            if change.design
            else None
        ),
        "items": [_item(item, state) for item in (change.tasks.items if change.tasks else ())],
        "problems": [
            {"path": p.path, "line": p.line, "code": p.code, "message": p.message}
            for p in change.problems
        ],
    }


def show_spec(record: Record, spec: Spec) -> Payload:
    """A spec, the deltas waiting for it, and its history from the archive."""
    pending = []
    for name in sorted(record.changes):
        delta = record.changes[name].deltas.get(spec.domain)
        if delta is not None:
            pending.append(
                {
                    "change": name,
                    "added": [item.name for item in delta.added],
                    "modified": [item.name for item in delta.modified],
                    "removed": [item.name for item in delta.removed],
                }
            )
    return {
        **_header("show.spec"),
        "name": spec.domain,
        "title": spec.title,
        "purpose": spec.purpose,
        "repos": list(spec.repos),
        "requirements": [
            {
                "name": requirement.name,
                "statement": requirement.statement,
                "scenarios": [
                    {
                        "name": scenario.name,
                        "steps": [
                            {"keyword": keyword, "text": text} for keyword, text in scenario.steps
                        ],
                    }
                    for scenario in requirement.scenarios
                ],
            }
            for requirement in spec.requirements
        ],
        "pending": pending,
        "history": [
            {"date": entry.date.isoformat(), "change": entry.change, "outcome": entry.outcome}
            for entry in spec_history(record, spec.domain)
        ],
    }


def show_milestone(record: Record, milestone: Milestone) -> Payload:
    """A milestone's goal and where each roadmap line stands."""
    state = milestone_state(record, milestone)
    return {
        **_header("show.milestone"),
        "name": milestone.name,
        "title": milestone.goal.title if milestone.goal else None,
        "goal": dict(milestone.goal.sections) if milestone.goal else None,
        "lines": [
            {"text": line.text, "change": line.change, "status": line.status.value}
            for line in state.lines
        ],
        "archived": state.archived,
        "total": state.total,
    }


def show_exploration(record: Record, exploration: Exploration) -> Payload:
    """An exploration and where it went."""
    state = exploration_state(record, exploration)
    return {
        **_header("show.exploration"),
        "name": exploration.name,
        "title": exploration.title,
        "status": state.status.value,
        "detail": state.detail,
        "sections": dict(exploration.sections),
    }


def _archived(record: Record, name: str) -> ArchiveEntry | None:
    matches = [
        entry
        for entry in record.archived_changes
        if name in (entry.name, entry.path.rsplit("/", 1)[-1])
    ]
    return max(matches) if matches else None


def show(record: Record, name: str, kind: str | None = None) -> Payload:
    """Everything about the one thing a name refers to.

    A name used by more than one kind needs ``kind`` to say which. An archived
    change is found by its name (the latest one) or by its dated folder name.
    """
    found: dict[str, Payload] = {}
    if kind in (None, "change"):
        archived = _archived(record, name)
        if name in record.changes:
            found["change"] = show_change(record, record.changes[name])
        elif archived is not None:
            found["change"] = show_change(record, load_archived_change(record, archived))
    if kind in (None, "spec") and name in record.specs:
        found["spec"] = show_spec(record, record.specs[name])
    if kind in (None, "milestone") and name in record.milestones:
        found["milestone"] = show_milestone(record, record.milestones[name])
    if kind in (None, "exploration") and name in record.explorations:
        found["exploration"] = show_exploration(record, record.explorations[name])
    if not found:
        what = f"{kind} named" if kind else "change, spec, milestone or exploration named"
        raise Refusal(f'There is no {what} "{name}". List what there is with "wm ls <kind>".')
    if len(found) > 1:
        kinds = " and ".join(found)
        raise Refusal(
            f'"{name}" is the name of a {kinds}. Say which one: '
            f"wm show {name} --kind {next(iter(found))}"
        )
    return next(iter(found.values()))

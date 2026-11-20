"""The data behind every view: plain payloads built from the record and its state.

A payload holds only JSON types. It carries its schema's name and version.
What it reads from this machine rather than the record (wm's own version,
the branches checked out in an atlas's repos, what the doctors find) is
named for what it is. Values that would put an absolute path in the JSON,
such as a repo's folder, sit under keys starting with an underscore: the
text views show them, and the JSON leaves them out.
"""

import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from waymark import __version__
from waymark.record.artifacts.changes import Change
from waymark.record.artifacts.config import RECORD_FORMAT
from waymark.record.artifacts.explorations import QUESTIONS, Exploration
from waymark.record.artifacts.milestones import Milestone
from waymark.record.artifacts.resources import Resource
from waymark.record.artifacts.specs import Spec
from waymark.record.artifacts.tasks import Item, ReviewRecord
from waymark.record.evidence.records import RecordKind
from waymark.record.machine import git
from waymark.record.machine.atlas import Location
from waymark.record.machine.branches import Branches as ChangeBranches
from waymark.record.machine.branches import ChangeBranch
from waymark.record.record import (
    ArchiveEntry,
    Record,
    load_archived_change,
    load_archived_exploration,
    spec_history,
)
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
from waymark.record.terms import Layout, Verdict
from waymark.services.check import Finding, Severity, check_record
from waymark.services.common import Refusal, repo_locations
from waymark.services.context import CONTEXT_VERSION, DELEGATED_VERSION

if TYPE_CHECKING:  # the doctor's checks reach the views through the CLI; no import cycle
    from waymark.services.doctor import Report
from waymark.services.instructions import INSTRUCTIONS_VERSION
from waymark.services.pr import PR_VERSION

Payload = dict[str, Any]

VERSIONS = {
    "status": 2,
    "inbox": 1,
    "ls": 1,
    "check": 1,
    "show.change": 5,
    "show.spec": 1,
    "show.milestone": 1,
    "show.exploration": 2,
    "show.resource": 1,
    "instructions": INSTRUCTIONS_VERSION,
    "context.explore": CONTEXT_VERSION,
    "context.implement": DELEGATED_VERSION,
    "context.review": DELEGATED_VERSION,
    "doctor": 1,
    "pr": PR_VERSION,
}
"""The schema version of each payload. A breaking change to a payload bumps its number."""

KINDS = ("change", "spec", "milestone", "exploration", "resource")
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


class _Branches:
    """The branch checked out in each repo of an atlas, read once per view."""

    def __init__(self, record: Record) -> None:
        self.record = record
        config = record.config
        atlas = record.layout is Layout.ATLAS and config is not None
        self.atlas = config.atlas_name if atlas and config else None
        self.locations: dict[str, Location] = repo_locations(record) if self.atlas else {}
        self._seen: dict[Path, str | None] = {}

    def _branch(self, folder: Path) -> str | None:
        if folder not in self._seen:
            self._seen[folder] = git.current_branch(folder)
        return self._seen[folder]

    def of(self, change: Change, state: ChangeState) -> list[Payload]:
        """Each repo a change touches, with its branch; a mismatch warns while it is applied."""
        if self.atlas is None:
            return []
        touched = sorted(
            {item.repo for item in change.tasks.items if item.repo} if change.tasks else ()
        )
        building = state.acceptance is AcceptanceState.VALID and not state.applied
        places: list[tuple[str, str, Path | None]] = [
            ("atlas", self.atlas, self.record.project.root)
        ]
        for repo in touched:
            location = self.locations.get(repo)
            places.append(("code", repo, location.folder if location else None))
        entries = []
        for kind, name, folder in places:
            branch = self._branch(folder) if folder is not None else None
            matches = branch == change.name
            entries.append(
                {
                    "name": name,
                    "kind": kind,
                    "found": folder is not None,
                    "branch": branch,
                    "matches": matches,
                    "warn": building and folder is not None and not matches,
                }
            )
        return entries


def _change_summary(
    state: ChangeState, place: ChangeBranch, repos: list[Payload] | None = None
) -> Payload:
    step = state.next_step
    return {
        "name": state.name,
        "branch": place.branch,
        "base": place.base,
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
        "repos": repos or [],
    }


def _entry(kind: str, summary: str, **fields: str | None) -> Payload:
    base: Payload = {"kind": kind, "change": None, "item": None, "exploration": None}
    return {**base, **fields, "summary": summary}


def _item_entries(name: str, change: Change, state: ChangeState) -> list[Payload]:
    entries: list[Payload] = []
    items = {item.number: item for item in (change.tasks.items if change.tasks else ())}
    command = f'wm resolve {name} {{}} "<what was decided>"'
    if state.review.escalated:
        records = change.tasks.review_records if change.tasks else ()
        last = records[-1] if records else None
        gap = last is not None and last.verdict is Verdict.SPEC_GAP
        entries.append(
            _entry(
                "spec-gap" if gap else "verdict",
                state.review.escalated,
                change=name,
                command=command.format("review"),
            )
        )
    for item_state in state.items:
        item = items[item_state.number]
        number = item.number
        if item_state.escalated:
            gap = item.spec_gap is not None
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
            command = f'wm archive {name} --built "<what was built>" --differs "<how it differs>"'
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
    branches = _Branches(record)
    places = ChangeBranches(record)
    return {
        **_header("status"),
        "layout": record.layout.value,
        "atlas": config.atlas_name if config else None,
        "wm_version": __version__,
        "pinned_version": config.wm_version if config else None,
        "writable": _writable(record),
        "default_branch": places.default,
        "changes": [
            _change_summary(
                state.changes[name],
                places.of(record.changes[name]),
                branches.of(record.changes[name], state.changes[name]),
            )
            for name in sorted(state.changes)
        ],
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


def ls(record: Record, kind: str, *, archived: bool = False, source: str | None = None) -> Payload:
    """One entry per change, spec, milestone or exploration, with its state.

    ``source`` names the referenced atlas the record was read from, if any.
    """
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
    elif kind == "resource":
        entries = [
            {
                "name": name,
                "state": resource.status or "unknown",
                "detail": f"{resource.kind or 'unknown'}, serves {_served(resource)}",
            }
            for name, resource in sorted(record.resources.items())
        ]
    else:
        entries = [
            {"name": name, "state": exploration.status.value, "detail": exploration.detail or ""}
            for name, exploration in sorted(state.explorations.items())
        ]
        if archived:
            entries.extend(
                {"name": entry.name, "state": "archived", "detail": entry.date.isoformat()}
                for entry in sorted(record.archived_explorations, reverse=True)
            )
    return {**_header("ls"), "kind": kind, "from": source, "entries": entries}


def _served(resource: Resource) -> str:
    return ", ".join(resource.serves) or "none"


def _record(record: ReviewRecord, numbers: tuple[str, ...] = ()) -> Payload:
    """A record as a payload; ``numbers`` are the change's items, which a review without
    ``covers`` covers."""
    reviews = record.kind in (RecordKind.REVIEW, RecordKind.SELF_REVIEW)
    return {
        "kind": record.kind.value,
        "line": record.line,
        "date": record.date.isoformat(),
        "by": record.who,
        "verdict": record.verdict.value if record.verdict else None,
        "text": record.text,
        "item": record.item,
        "items": list(record.covers if record.kind is RecordKind.ACCEPTED else record.items),
        "covers": list(record.covers or numbers) if reviews else [],
        "findings": [
            {"severity": f.severity.value, "place": f.place, "text": f.text}
            for f in record.findings
        ],
        "details": list(record.details),
    }


def _change_review(record: Record, change: Change, state: ChangeState | None) -> Payload:
    """The change's review: its level, whether it is done, and its records with findings."""
    review = state.review if state else None
    return {
        "level": (review.level if review else change.review_level(record.default_review)).value,
        "reviewed": review.reviewed if review else None,
        "reopen": list(review.reopen) if review else [],
        "needs_human": review.escalated if review else None,
    }


def _item(item: Item, state: ChangeState | None) -> Payload:
    item_state = next((i for i in state.items if i.number == item.number), None) if state else None
    return {
        "number": item.number,
        "title": item.title,
        "ticked": item.ticked,
        "build": item.build.value if item.build else None,
        "needs_human": item_state.escalated if item_state else None,
        "criteria": item.criteria,
        "verify": item.verify,
        "repo": item.repo,
        "blocked": item.blocked,
        "spec_gap": item.spec_gap,
        "records": [_record(record) for record in item.records],
    }


def show_change(record: Record, change: Change) -> Payload:
    """Everything about one change, active or archived."""
    active = change.archived_on is None
    state = change_state(record, change, overlaps(record)) if active else None
    proposal = change.proposal
    numbers = tuple(item.number for item in change.tasks.items) if change.tasks else ()
    return {
        **_header("show.change"),
        "name": change.name,
        "path": change.path,
        "archived_on": change.archived_on.isoformat() if change.archived_on else None,
        "title": proposal.title if proposal else None,
        "state": (
            _change_summary(
                state, ChangeBranches(record).of(change), _Branches(record).of(change, state)
            )
            if state
            else None
        ),
        "owner": proposal.owner if proposal else None,
        "accepted": (
            {"date": change.acceptance.date.isoformat(), "by": change.acceptance.who}
            if change.acceptance
            else None
        ),
        "synced_on": change.synced.isoformat() if change.synced else None,
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
        "review": _change_review(record, change, state),
        "log": [_record(r, numbers) for r in (change.tasks.log if change.tasks else ())],
        "problems": [
            {"path": p.path, "line": p.line, "code": p.code, "message": p.message}
            for p in change.problems
        ],
    }


def show_spec(record: Record, spec: Spec, source: str | None = None) -> Payload:
    """A spec, the deltas waiting for it, and its history from the archive.

    ``source`` names the referenced atlas the spec was read from, if any.
    """
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
        "from": source,
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


def show_exploration(
    record: Record, exploration: Exploration, archived_on: datetime.date | None = None
) -> Payload:
    """An exploration and where it went, with the day it was archived, if it was."""
    state = exploration_state(record, exploration)
    return {
        **_header("show.exploration"),
        "name": exploration.name,
        "title": exploration.title,
        "status": state.status.value,
        "detail": state.detail,
        "archived_on": archived_on.isoformat() if archived_on else None,
        "sections": dict(exploration.sections),
    }


def show_resource(resource: Resource) -> Payload:
    """A resource in full: its lines, then its sections."""
    return {
        **_header("show.resource"),
        "name": resource.name,
        "title": resource.title,
        "kind": resource.kind,
        "serves": list(resource.serves),
        "status": resource.status,
        "verified": resource.verified.isoformat() if resource.verified else None,
        "sections": dict(resource.sections),
    }


def _archived(
    name: str, entries: tuple[ArchiveEntry, ...], suffix: str = ""
) -> ArchiveEntry | None:
    """The latest archived entry a name refers to: its own name, or its dated name."""
    matches = [
        entry
        for entry in entries
        if name in (entry.name, entry.path.rsplit("/", 1)[-1].removesuffix(suffix))
    ]
    return max(matches) if matches else None


def show(record: Record, name: str, kind: str | None = None) -> Payload:
    """Everything about the one thing a name refers to.

    A name used by more than one kind needs ``kind`` to say which. An archived
    change is found by its name (the latest one) or by its dated folder name.
    """
    found: dict[str, Payload] = {}
    if kind in (None, "change"):
        archived = _archived(name, record.archived_changes)
        if name in record.changes:
            found["change"] = show_change(record, record.changes[name])
        elif archived is not None:
            found["change"] = show_change(record, load_archived_change(record, archived))
    if kind in (None, "spec") and name in record.specs:
        found["spec"] = show_spec(record, record.specs[name])
    if kind in (None, "milestone") and name in record.milestones:
        found["milestone"] = show_milestone(record, record.milestones[name])
    if kind in (None, "exploration"):
        _find_exploration(record, name, found)
    if kind in (None, "resource") and name in record.resources:
        found["resource"] = show_resource(record.resources[name])
    if not found:
        what = f"{kind} named" if kind else "change, spec, milestone, exploration or resource named"
        raise Refusal(f'There is no {what} "{name}". List what there is with "wm ls <kind>".')
    if len(found) > 1:
        kinds = " and ".join(found)
        raise Refusal(
            f'"{name}" is the name of a {kinds}. Say which one: '
            f"wm show {name} --kind {next(iter(found))}"
        )
    return next(iter(found.values()))


def _find_exploration(record: Record, name: str, found: dict[str, Payload]) -> None:
    """An active exploration by name, else an archived one by its name or dated name."""
    if name in record.explorations:
        found["exploration"] = show_exploration(record, record.explorations[name])
        return
    entry = _archived(name, record.archived_explorations, ".md")
    exploration = load_archived_exploration(record, entry) if entry else None
    if entry is not None and exploration is not None:
        found["exploration"] = show_exploration(record, exploration, entry.date)


def doctor(report: "Report") -> Payload:
    """What a doctor found on this machine. Each check's folder is shown in text only."""
    return {
        **_header("doctor"),
        "scope": report.scope,
        "ok": not report.failed,
        "checks": [
            {
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "_folder": str(check.folder) if check.folder is not None else None,
            }
            for check in report.checks
        ],
    }

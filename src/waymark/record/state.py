"""State, derived from the files on every call. Nothing here is stored.

A change's phase, acceptance, progress, conflicts and next step all follow from
which files exist and what they contain, so the same files always give the same
state.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from waymark.record.changes import DESIGN_FILE, PROPOSAL_FILE, SPECS_DIR, TASKS_FILE, Change
from waymark.record.deltas import delta_mismatches
from waymark.record.explorations import Exploration
from waymark.record.fingerprint import change_fingerprint
from waymark.record.links import resolve
from waymark.record.milestones import Milestone
from waymark.record.names import parse_archive_name
from waymark.record.record import ARCHIVE, CHANGES, MILESTONES, Record
from waymark.record.tasks import Item, RecordKind
from waymark.record.terms import Phase, ReviewLevel, Verdict

ESCALATE_AFTER_CHANGES = 2
"""How many "changes" verdicts on one item send it to the human."""


class AcceptanceState(StrEnum):
    """Whether a change is accepted as it now stands."""

    MISSING = "missing"
    VALID = "valid"
    WITHDRAWN = "withdrawn"


class ConflictKind(StrEnum):
    """How a change's deltas clash with the specs or with another change.

    A mismatch is a delta that doesn't apply to its spec as it now stands; it
    blocks the change. An overlap is two active changes naming the same
    requirement; it is reported, and resolved when the first one is archived:
    the other's acceptance is then withdrawn, or its delta becomes a mismatch.
    """

    MISMATCH = "mismatch"
    OVERLAP = "overlap"


class StepKind(StrEnum):
    """What comes next for a change."""

    PROPOSE = "propose"
    SPECS = "specs"
    DESIGN = "design"
    TASKS = "tasks"
    RESOLVE_CONFLICT = "resolve-conflict"
    ACCEPT = "accept"
    APPLY = "apply"
    REVIEW = "review"
    RESOLVE_ITEMS = "resolve-items"
    ARCHIVE = "archive"


class RoadmapStatus(StrEnum):
    """Where a roadmap line's change stands."""

    PLANNED = "planned"
    ACTIVE = "active"
    ARCHIVED = "archived"
    MISSING = "missing"


class ExplorationStatus(StrEnum):
    """Where an exploration went, read from its conclusion."""

    OPEN = "open"
    PARKED = "parked"
    LED_TO = "led-to"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Conflict:
    """One clash, with the changes it involves and what to do about it."""

    kind: ConflictKind
    domain: str
    requirement: str | None
    changes: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class NextStep:
    """The first thing missing on a change's way to being applied and archived.

    ``human`` marks the steps only the human can take.
    """

    kind: StepKind
    item: str | None = None
    human: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ItemState:
    """Where one task item stands.

    ``level`` is the review the item now needs: its own level, or independent
    once a reviewer has asked for changes. ``escalated`` says why the item has
    gone to the human, if it has.
    """

    number: str
    title: str
    level: ReviewLevel
    ticked: bool
    reviewed: bool
    blocked: str | None
    redo: bool
    escalated: str | None


@dataclass(frozen=True)
class ChangeState:
    """Where one active change stands."""

    name: str
    owner: str | None
    short_path: bool
    phase: Phase
    acceptance: AcceptanceState
    ticked: int
    total: int
    items: tuple[ItemState, ...]
    conflicts: tuple[Conflict, ...]
    next_step: NextStep

    @property
    def applied(self) -> bool:
        return self.phase is Phase.APPLIED


@dataclass(frozen=True)
class RoadmapLine:
    """A roadmap line and the change it points at, if any."""

    text: str
    change: str | None
    status: RoadmapStatus


@dataclass(frozen=True)
class MilestoneState:
    """A milestone's member changes, and how many of them are archived."""

    name: str
    lines: tuple[RoadmapLine, ...]
    archived: int
    total: int


@dataclass(frozen=True)
class ExplorationState:
    """An exploration's state, and what it led to or why it was parked."""

    name: str
    status: ExplorationStatus
    detail: str | None


@dataclass(frozen=True)
class RecordState:
    """The state of everything active in the record."""

    changes: Mapping[str, ChangeState]
    overlaps: tuple[Conflict, ...]
    milestones: Mapping[str, MilestoneState]
    explorations: Mapping[str, ExplorationState]


def item_state(item: Item, default: ReviewLevel) -> ItemState:
    """Derive one item's state from its tick and its review records."""
    last = item.records[-1] if item.records else None
    changes = sum(1 for record in item.records if record.verdict is Verdict.CHANGES)
    level = ReviewLevel.INDEPENDENT if changes else item.level(default)

    escalated: str | None = None
    redo = False
    if last is not None and last.verdict is Verdict.SPEC_GAP:
        escalated = "the reviewer found a spec gap"
    elif last is not None and last.verdict is Verdict.CHANGES:
        if changes >= ESCALATE_AFTER_CHANGES:
            escalated = "a second review asked for changes"
        else:
            redo = True

    passed = last is not None and last.verdict is Verdict.PASS
    if level is ReviewLevel.NONE:
        reviewed = True
    elif level is ReviewLevel.SELF:
        reviewed = passed or (last is not None and last.kind is RecordKind.SELF_REVIEW)
    else:
        reviewed = passed
    return ItemState(
        number=item.number,
        title=item.title,
        level=level,
        ticked=item.ticked,
        reviewed=item.ticked and reviewed,
        blocked=item.blocked,
        redo=redo,
        escalated=escalated,
    )


def acceptance_state(record: Record, change: Change) -> AcceptanceState:
    """Whether the change has an acceptance, and whether it still covers the change."""
    acceptance = change.proposal.acceptance if change.proposal else None
    if acceptance is None:
        return AcceptanceState.MISSING
    current = change_fingerprint(change, record.specs, record.default_review)
    return AcceptanceState.VALID if acceptance.fingerprint == current else AcceptanceState.WITHDRAWN


def mismatches(record: Record, change: Change) -> tuple[Conflict, ...]:
    """The change's deltas that don't apply to their specs as they now stand."""
    found: list[Conflict] = []
    for domain in sorted(change.deltas):
        delta = change.deltas[domain]
        if delta.problems:
            continue
        found.extend(
            Conflict(ConflictKind.MISMATCH, domain, None, (change.name,), problem.message)
            for problem in delta_mismatches(record.specs.get(domain), delta)
        )
    return tuple(found)


def overlaps(record: Record) -> tuple[Conflict, ...]:
    """Requirements that more than one active change adds, modifies or removes."""
    touched: dict[tuple[str, str], tuple[str, set[str]]] = {}
    for name in sorted(record.changes):
        for domain, delta in record.changes[name].deltas.items():
            for key, requirement in delta.touched():
                touched.setdefault((domain, key), (requirement, set()))[1].add(name)
    found: list[Conflict] = []
    for (domain, _), (requirement, names) in sorted(touched.items()):
        if len(names) > 1:
            changes = tuple(sorted(names))
            message = (
                f'{" and ".join(changes)} both change the requirement "{requirement}" in the '
                f'spec "{domain}". Whichever is archived first wins; the other must then be '
                "revised against the new spec and accepted again."
            )
            found.append(Conflict(ConflictKind.OVERLAP, domain, requirement, changes, message))
    return tuple(found)


def _artifact_step(change: Change) -> tuple[Phase, NextStep] | None:
    """The first artifact that is missing or has problems, with the phase reached so far."""

    def reason(relative: str, missing: str) -> str:
        found = change.problems_in(relative)
        return found[0].message if found else missing

    proposal = change.proposal
    if proposal is None or change.problems_in(PROPOSAL_FILE):
        step = NextStep(StepKind.PROPOSE, reason=reason(PROPOSAL_FILE, "Draft the proposal."))
        return Phase.PROPOSED, step

    no_deltas_needed = proposal.no_spec_changes and not change.deltas
    if change.problems_in(SPECS_DIR) or not (change.deltas or no_deltas_needed):
        missing = 'Draft the deltas, or state "No spec changes" under the proposal\'s impact.'
        return Phase.PROPOSED, NextStep(StepKind.SPECS, reason=reason(SPECS_DIR, missing))

    reached = Phase.SPECIFIED
    if change.problems_in(DESIGN_FILE) or (change.design is None and not change.short_path):
        step = NextStep(StepKind.DESIGN, reason=reason(DESIGN_FILE, "Draft the design."))
        return reached, step
    if not change.short_path:
        reached = Phase.DESIGNED

    tasks = change.tasks
    if tasks is None or not tasks.items or change.problems_in(TASKS_FILE):
        step = NextStep(StepKind.TASKS, reason=reason(TASKS_FILE, "Draft the task list."))
        return reached, step
    return None


def _item_step(items: tuple[ItemState, ...]) -> NextStep:
    """The next item to apply or review, or what waits on the human."""
    waiting: list[ItemState] = []
    for item in items:
        if item.escalated:
            waiting.append(item)
        elif item.redo:
            return NextStep(
                StepKind.APPLY, item.number, reason="Reopen the item: the review asked for changes."
            )
        elif not item.ticked:
            if item.blocked:
                waiting.append(item)
            else:
                return NextStep(StepKind.APPLY, item.number)
        elif not item.reviewed:
            return NextStep(StepKind.REVIEW, item.number, reason=f"Review level: {item.level}.")
    if waiting:
        first = waiting[0]
        why = first.escalated or f"blocked: {first.blocked}"
        return NextStep(StepKind.RESOLVE_ITEMS, first.number, human=True, reason=why)
    return NextStep(StepKind.ARCHIVE, human=True)


def change_state(
    record: Record, change: Change, record_overlaps: tuple[Conflict, ...] = ()
) -> ChangeState:
    """Derive one active change's state."""
    default = record.default_review
    items = tuple(
        item_state(item, default) for item in (change.tasks.items if change.tasks else ())
    )
    blocking = mismatches(record, change)
    conflicts = (*blocking, *(c for c in record_overlaps if change.name in c.changes))
    acceptance = acceptance_state(record, change)

    ticked = any(item.ticked for item in items)
    drafting = _artifact_step(change)
    if drafting is not None:
        phase, next_step = drafting
    elif acceptance is not AcceptanceState.VALID:
        phase = Phase.PLANNED
        why = (
            "The change was edited after it was accepted, or a spec it changes has moved on."
            if acceptance is AcceptanceState.WITHDRAWN
            else ""
        )
        next_step = NextStep(StepKind.ACCEPT, human=True, reason=why)
    else:
        next_step = _item_step(items)
        if next_step.kind is StepKind.ARCHIVE and not blocking:
            phase = Phase.APPLIED
        else:
            phase = Phase.APPLYING if ticked else Phase.ACCEPTED
    if drafting is None and blocking:
        next_step = NextStep(StepKind.RESOLVE_CONFLICT, reason=blocking[0].message)

    return ChangeState(
        name=change.name,
        owner=change.proposal.owner if change.proposal else None,
        short_path=change.short_path,
        phase=phase,
        acceptance=acceptance,
        ticked=sum(1 for item in items if item.ticked),
        total=len(items),
        items=items,
        conflicts=tuple(conflicts),
        next_step=next_step,
    )


@dataclass(frozen=True)
class _Member:
    """The change or milestone a link points into."""

    name: str
    folder: str
    archived: bool


def _member(doc_path: str, target: str, kind: str) -> _Member | None:
    """Read a link as pointing into a change or milestone folder, active or archived."""
    resolved = resolve(doc_path, target)
    parts = resolved.split("/") if resolved else []
    if len(parts) > 1 and parts[0] == kind and parts[1] != ARCHIVE:
        return _Member(parts[1], "/".join(parts[:2]), archived=False)
    if len(parts) > 2 and parts[0] == kind:  # noqa: PLR2004
        archived = parse_archive_name(parts[2])
        if archived is not None:
            return _Member(archived.name, "/".join(parts[:3]), archived=True)
    return None


def milestone_state(record: Record, milestone: Milestone) -> MilestoneState:
    """Derive a milestone's membership and progress from its roadmap's links."""
    lines: list[RoadmapLine] = []
    archived_folders = {entry.path for entry in record.archived_changes}
    roadmap = milestone.roadmap
    for entry in roadmap.entries if roadmap else ():
        member = (
            _member(roadmap.doc.path, entry.target, CHANGES) if roadmap and entry.target else None
        )
        if member is None:
            lines.append(RoadmapLine(entry.text, None, RoadmapStatus.PLANNED))
        elif member.archived:
            found = member.folder in archived_folders
            status = RoadmapStatus.ARCHIVED if found else RoadmapStatus.MISSING
            lines.append(RoadmapLine(entry.text, member.name, status))
        else:
            status = (
                RoadmapStatus.ACTIVE if member.name in record.changes else RoadmapStatus.MISSING
            )
            lines.append(RoadmapLine(entry.text, member.name, status))
    members = [line for line in lines if line.change is not None]
    done = sum(1 for line in members if line.status is RoadmapStatus.ARCHIVED)
    return MilestoneState(milestone.name, tuple(lines), done, len(members))


def exploration_state(record: Record, exploration: Exploration) -> ExplorationState:
    """Derive an exploration's state from its conclusion."""
    if not exploration.conclusion:
        return ExplorationState(exploration.name, ExplorationStatus.OPEN, None)
    if exploration.parked is not None:
        return ExplorationState(exploration.name, ExplorationStatus.PARKED, exploration.parked)
    for target in exploration.conclusion_links:
        for folder in (CHANGES, MILESTONES):
            member = _member(exploration.doc.path, target, folder)
            if member is not None:
                kind = "change" if folder == CHANGES else "milestone"
                return ExplorationState(
                    exploration.name, ExplorationStatus.LED_TO, f"{kind} {member.name}"
                )
    return ExplorationState(
        exploration.name,
        ExplorationStatus.UNREADABLE,
        'The conclusion must be empty, "Parked: <reason>", or a link to a change or milestone.',
    )


def derive_state(record: Record) -> RecordState:
    """Derive the state of every active change, milestone and exploration."""
    record_overlaps = overlaps(record)
    return RecordState(
        changes={
            name: change_state(record, change, record_overlaps)
            for name, change in record.changes.items()
        },
        overlaps=record_overlaps,
        milestones={
            name: milestone_state(record, milestone)
            for name, milestone in record.milestones.items()
        },
        explorations={
            name: exploration_state(record, exploration)
            for name, exploration in record.explorations.items()
        },
    )

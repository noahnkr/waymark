"""State, derived from the files on every call. Nothing here is stored.

A change's phase, acceptance, progress, conflicts and next step all follow from
which files exist and what they contain, so the same files always give the same
state.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from waymark.record.changes import DESIGN_FILE, PROPOSAL_FILE, SPECS_DIR, TASKS_FILE, Change
from waymark.record.deltas import delta_is_merged, delta_mismatches
from waymark.record.explorations import Exploration
from waymark.record.fingerprint import change_fingerprint
from waymark.record.links import resolve
from waymark.record.milestones import Milestone, RoadmapEntry
from waymark.record.names import is_valid_name, parse_archive_name
from waymark.record.record import ARCHIVE, CHANGES, MILESTONES, Record
from waymark.record.records import RecordKind
from waymark.record.tasks import Item, ReviewRecord
from waymark.record.terms import Phase, ReviewLevel, Verdict

ESCALATE_AFTER_CHANGES = 2
"""How many "changes" verdicts on one change send it to the human."""


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

    ``redo`` marks an item a review named to rebuild that hasn't been reopened
    yet. ``escalated`` says why the item has gone to the human, if it has.
    """

    number: str
    title: str
    ticked: bool
    blocked: str | None
    redo: bool
    escalated: str | None


@dataclass(frozen=True)
class ReviewState:
    """Where the change's review stands.

    ``level`` is the review the change now needs: its own level, or independent
    once a review has asked for changes. ``reviewed`` is true once every item is
    ticked, the review the level asks for is recorded, and that review or an
    earlier one covers each item. ``reopen`` lists the items the last request
    for changes named that still wait to be reopened. ``uncovered`` lists the
    ticked items no passing review covers, once some review has passed: items
    added after it, which need a review of their own. ``to_review`` lists the
    items the next review is of: ``uncovered`` when there are any, else every
    item. ``escalated`` says why the review has gone to the human, if it has.
    """

    level: ReviewLevel
    reviewed: bool
    reopen: tuple[str, ...]
    escalated: str | None
    uncovered: tuple[str, ...] = ()
    to_review: tuple[str, ...] = ()


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
    review: ReviewState
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


def _times_named(records: tuple[ReviewRecord, ...], number: str) -> int:
    """How many requests for changes named an item to rebuild.

    A request the human resolved right after it is closed: what it named is not
    rebuilt unless a later review asks again.
    """
    count = 0
    for position, record in enumerate(records):
        following = records[position + 1] if position + 1 < len(records) else None
        closed = following is not None and following.kind is RecordKind.RESOLVED
        if record.verdict is Verdict.CHANGES and number in record.items and not closed:
            count += 1
    return count


def item_state(item: Item, review_records: tuple[ReviewRecord, ...] = ()) -> ItemState:
    """Derive one item's state from its tick, its blocker, its spec gap and its reopenings.

    An item is to be rebuilt while more requests for changes have named it than
    it has been reopened.
    """
    reopened = sum(1 for record in item.records if record.kind is RecordKind.REOPENED)
    escalated = (
        f"the builder found a spec gap: {item.spec_gap}" if item.spec_gap is not None else None
    )
    return ItemState(
        number=item.number,
        title=item.title,
        ticked=item.ticked,
        blocked=item.blocked,
        redo=escalated is None and _times_named(review_records, item.number) > reopened,
        escalated=escalated,
    )


def review_state(change: Change, default: ReviewLevel) -> ReviewState:
    """Derive the change's review from the records in its Log.

    A ``(resolved)`` record closes whatever came before it: requests for changes
    are counted from the last one on.
    """
    tasks = change.tasks
    records = tasks.review_records if tasks else ()
    items = tasks.items if tasks else ()
    last = records[-1] if records else None
    resolved = [index for index, record in enumerate(records) if record.kind is RecordKind.RESOLVED]
    recent = records[resolved[-1] + 1 :] if resolved else records
    changes = sum(1 for record in recent if record.verdict is Verdict.CHANGES)
    ever_changes = any(record.verdict is Verdict.CHANGES for record in records)
    level = ReviewLevel.INDEPENDENT if ever_changes else change.review_level(default)

    escalated: str | None = None
    if last is not None and last.verdict is Verdict.SPEC_GAP:
        escalated = f"the reviewer found a spec gap: {last.text}"
    elif last is not None and last.verdict is Verdict.CHANGES and changes >= ESCALATE_AFTER_CHANGES:
        escalated = f"a second review asked for changes: {last.text}"

    reopen = tuple(
        item.number for item in items if escalated is None and item_state(item, records).redo
    )
    passing = [record for record in records if _counts_at(record, level)]
    recorded = level is ReviewLevel.NONE or (last is not None and _counts_at(last, level))
    numbers = tuple(item.number for item in items)
    uncovered: tuple[str, ...] = ()
    if passing and level is not ReviewLevel.NONE:
        covered = {number for record in passing for number in _covered(record, numbers)}
        uncovered = tuple(
            item.number for item in items if item.ticked and item.number not in covered
        )
    every_item = bool(items) and all(item.ticked for item in items)
    return ReviewState(
        level=level,
        reviewed=every_item and recorded and not uncovered,
        reopen=reopen,
        escalated=escalated,
        uncovered=uncovered,
        to_review=uncovered or numbers,
    )


def _counts_at(record: ReviewRecord, level: ReviewLevel) -> bool:
    """Whether a record is a passing review at the level: a pass, or at self also a self-review."""
    if record.verdict is Verdict.PASS:
        return True
    return level is ReviewLevel.SELF and record.kind is RecordKind.SELF_REVIEW


def _covered(record: ReviewRecord, numbers: tuple[str, ...]) -> tuple[str, ...]:
    """The items a review covers: those it names, or every item when it names none."""
    return record.covers or numbers


def acceptance_state(record: Record, change: Change) -> AcceptanceState:
    """Whether the change has an acceptance, and whether it still covers the change."""
    acceptance = change.acceptance
    if acceptance is None:
        return AcceptanceState.MISSING
    current = change_fingerprint(change, record.specs, record.default_review, acceptance.items)
    return AcceptanceState.VALID if acceptance.fingerprint == current else AcceptanceState.WITHDRAWN


def mismatches(record: Record, change: Change) -> tuple[Conflict, ...]:
    """The change's deltas that don't apply to their specs as they now stand.

    Once a change is synced, its deltas are already in the specs; a mismatch is
    then a spec that has moved on since.
    """
    synced = change.synced is not None
    found: list[Conflict] = []
    for domain in sorted(change.deltas):
        delta = change.deltas[domain]
        spec = record.specs.get(domain)
        if delta.problems:
            continue
        if synced:
            if not delta_is_merged(spec, delta):
                message = (
                    f'The change was synced, but the spec "{domain}" no longer matches its '
                    "delta. Revise the delta to match the spec, or have the human remove the "
                    '"(synced)" record from the task list\'s Log and sync again.'
                )
                found.append(Conflict(ConflictKind.MISMATCH, domain, None, (change.name,), message))
            continue
        found.extend(
            Conflict(ConflictKind.MISMATCH, domain, None, (change.name,), problem.message)
            for problem in delta_mismatches(spec, delta)
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
        missing = 'Draft the deltas, or write "- Specs: none" under the proposal\'s Impact.'
        return Phase.PROPOSED, NextStep(StepKind.SPECS, reason=reason(SPECS_DIR, missing))

    reached = Phase.SPECIFIED
    if change.problems_in(DESIGN_FILE) or (change.design is None and not change.short_path):
        step = NextStep(StepKind.DESIGN, reason=reason(DESIGN_FILE, "Draft the design."))
        return reached, step
    if change.design is not None and (unsettled := change.design.unsettled):
        settle = "Settle the design before it is accepted: " + "; ".join(unsettled) + "."
        return reached, NextStep(StepKind.DESIGN, reason=settle)
    if not change.short_path:
        reached = Phase.DESIGNED

    tasks = change.tasks
    if tasks is None or not tasks.items or change.problems_in(TASKS_FILE):
        step = NextStep(StepKind.TASKS, reason=reason(TASKS_FILE, "Draft the task list."))
        return reached, step
    return None


def _named(numbers: tuple[str, ...]) -> str:
    """Item numbers as a sentence names them: "item 1.3" or "items 1.3, 1.4"."""
    return f"item {numbers[0]}" if len(numbers) == 1 else f"items {', '.join(numbers)}"


def _item_step(items: tuple[ItemState, ...], review: ReviewState) -> NextStep:
    """The next item to apply, the change's review, or what waits on the human."""
    if review.escalated:
        return NextStep(StepKind.RESOLVE_ITEMS, human=True, reason=review.escalated)
    for item in items:
        if item.redo and item.number in review.reopen:
            return NextStep(
                StepKind.APPLY, item.number, reason="Reopen the item: the review asked for changes."
            )
    waiting: list[ItemState] = []
    for item in items:
        if item.escalated or (item.blocked and not item.ticked):
            waiting.append(item)
        elif not item.ticked:
            return NextStep(StepKind.APPLY, item.number)
    if waiting:
        first = waiting[0]
        why = first.escalated or f"blocked: {first.blocked}"
        return NextStep(StepKind.RESOLVE_ITEMS, first.number, human=True, reason=why)
    if not review.reviewed:
        reason = f"Review level: {review.level}."
        if review.uncovered:
            reason += f" Review {_named(review.uncovered)} only: no passing review covers them."
        return NextStep(StepKind.REVIEW, reason=reason)
    return NextStep(StepKind.ARCHIVE, human=True)


def change_state(
    record: Record, change: Change, record_overlaps: tuple[Conflict, ...] = ()
) -> ChangeState:
    """Derive one active change's state."""
    review_records = change.tasks.review_records if change.tasks else ()
    items = tuple(
        item_state(item, review_records) for item in (change.tasks.items if change.tasks else ())
    )
    review = review_state(change, record.default_review)
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
        next_step = _item_step(items, review)
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
        review=review,
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


def entry_change(doc_path: str, entry: RoadmapEntry) -> str | None:
    """The change a roadmap line is for: the one it links, or a planned line's leading name."""
    if entry.target is not None:
        member = _member(doc_path, entry.target, CHANGES)
        return member.name if member else None
    name = entry.text.split(":", 1)[0].strip()
    return name if is_valid_name(name) else None


def milestone_links(record: Record) -> dict[str, tuple[str, ...]]:
    """For each active change, the active milestones whose roadmap links its proposal."""
    links: dict[str, list[str]] = {name: [] for name in record.changes}
    for name, milestone in sorted(record.milestones.items()):
        roadmap = milestone.roadmap
        for entry in roadmap.entries if roadmap else ():
            member = (
                _member(roadmap.doc.path, entry.target, CHANGES)
                if roadmap and entry.target
                else None
            )
            if (
                member
                and not member.archived
                and member.name in links
                and name not in links[member.name]
            ):
                links[member.name].append(name)
    return {change: tuple(names) for change, names in links.items()}


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
    """Derive an exploration's state from its status line."""
    if exploration.status is None:
        return ExplorationState(exploration.name, ExplorationStatus.OPEN, None)
    return _state_from_status(exploration)


def _state_from_status(exploration: Exploration) -> ExplorationState:
    if exploration.status == "parked":
        return ExplorationState(exploration.name, ExplorationStatus.PARKED, exploration.parked)
    if exploration.status == "led-to":
        for target in exploration.status_links:
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
            'A "led-to" status links to a change or milestone in the record.',
        )
    return ExplorationState(exploration.name, ExplorationStatus.OPEN, None)


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

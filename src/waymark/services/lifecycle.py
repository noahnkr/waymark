"""The lifecycle: accepting a change, recording evidence, syncing and archiving.

Every gate lives here. A refused command changes nothing and says what to do.
wm writes the evidence itself; these functions are the only way it gets written.
"""

import dataclasses
import datetime
from collections.abc import Sequence
from pathlib import Path

from waymark.record.artifacts.changes import Change
from waymark.record.artifacts.deltas import merge_delta
from waymark.record.artifacts.explorations import (
    LED_TO,
    OPEN,
    STATUS,
    parse_exploration,
    with_dropped,
)
from waymark.record.artifacts.milestones import MILESTONE_FILE, append_milestone_log
from waymark.record.artifacts.proposal import BUILT, DIFFERS, NONE, Proposal
from waymark.record.artifacts.specs import Spec, parse_spec
from waymark.record.artifacts.tasks import Tasks, parse_tasks
from waymark.record.evidence import records
from waymark.record.evidence.fingerprint import change_fingerprint
from waymark.record.evidence.records import RecordError, RecordKind
from waymark.record.machine import git
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.text import Document
from waymark.record.names import ArchiveName
from waymark.record.record import ARCHIVE, CHANGES, EXPLORATIONS, MILESTONES, SPECS, Record
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    ConflictKind,
    ItemState,
    RoadmapStatus,
    StepKind,
    led_to_done,
    milestone_state,
)
from waymark.record.terms import BuildRole, ReviewLevel, ReviewSeverity, Verdict
from waymark.record.writing.edits import append_log, set_outcome
from waymark.record.writing.moves import rewrite_links, tick_roadmap_lines
from waymark.record.writing.store import Transaction
from waymark.services.common import (
    Done,
    Refusal,
    commit,
    find_change,
    find_item,
    one_line,
    open_record,
    repo_locations,
    state_of,
)

REVIEW_TARGET = "review"
_DRAFTING = (StepKind.PROPOSE, StepKind.SPECS, StepKind.DESIGN, StepKind.TASKS)


def _open(start: Path, name: str) -> tuple[Record, Change, ChangeState]:
    record = open_record(start, writing=True)
    change = find_change(record, name)
    return record, change, state_of(record, change)


def _require_accepted(state: ChangeState) -> None:
    """The accept gate: no item of an unaccepted change is applied."""
    if state.acceptance is AcceptanceState.MISSING:
        raise Refusal(
            f'The change "{state.name}" is not accepted, so its items can\'t be applied yet. '
            f'The human accepts it with "wm accept {state.name}".'
        )
    if state.acceptance is AcceptanceState.WITHDRAWN:
        raise Refusal(
            f'The acceptance of "{state.name}" was withdrawn: the change was edited after it '
            "was accepted, or a spec it changes has moved on. The human accepts it again with "
            f'"wm accept {state.name}".'
        )


def _item_state(state: ChangeState, number: str) -> ItemState:
    return next(item for item in state.items if item.number == number)


def _tasks(change: Change) -> Tasks:
    assert change.tasks is not None
    return change.tasks


def _write_tasks(record: Record, change: Change, text: str) -> tuple[str, ...]:
    transaction = Transaction(record.files)
    transaction.write(_tasks(change).doc.path, text)
    return commit(transaction)


def _who(record: Record, kind: RecordKind, by: str | None, *, human: bool = False) -> str | None:
    """Who a record names: --by, else whoever its kind names."""
    try:
        return records.who_for(record.project.root, kind, by, human=human)
    except RecordError as error:
        raise Refusal(str(error)) from error


def _details(details: Sequence[str]) -> tuple[str, ...]:
    """The details to write under a record, each checked; refused before anything is written."""
    try:
        return tuple(records.check_detail(detail) for detail in details)
    except RecordError as error:
        raise Refusal(str(error)) from error


def _render(entry: records.Record) -> str:
    try:
        return records.render(entry)
    except RecordError as error:
        raise Refusal(str(error)) from error


def _today(today: datetime.date | None) -> datetime.date:
    return today if today is not None else datetime.date.today()


def accept(start: Path, name: str, today: datetime.date, *, by: str | None = None) -> Done:
    """Accept a change: record the acceptance with the change's fingerprint."""
    record, change, state = _open(start, name)
    step = state.next_step
    if step.kind in _DRAFTING:
        raise Refusal(
            f'The change "{name}" isn\'t ready to accept: its next step is "{step.kind}". '
            f"{step.reason}"
        )
    if step.kind is StepKind.RESOLVE_CONFLICT:
        raise Refusal(f'The change "{name}" has a conflict to resolve first. {step.reason}')
    if state.acceptance is AcceptanceState.VALID:
        return Done(f'The change "{name}" is already accepted as it stands.')
    if _unrevised(change):
        raise Refusal(
            f'The change "{name}" was accepted before, and nothing records what changed since. '
            f'Record it first with "wm revise {name} "<why>" --parts <part>,...", naming the '
            "parts the edit changed, then accept it again."
        )
    if by is not None:
        who: str | None = _who(record, RecordKind.ACCEPTED, by)
    else:
        who = git.user_name(record.project.root)
        if who:
            try:
                who = records.check_who(who)
            except RecordError as error:
                raise Refusal(f"{error} Set another name in git, or pass --by.") from error
    if not who:
        raise Refusal(
            "The acceptance records who accepted. Set your name in git: "
            'git config user.name "<name>".'
        )
    assert change.proposal is not None
    items = [item.number for item in change.tasks.items] if change.tasks else []
    fingerprint = change_fingerprint(change, record.specs, record.default_review, items)
    entry = records.Record(
        RecordKind.ACCEPTED, today, who=who, fingerprint=fingerprint, items=tuple(items)
    )
    transaction = Transaction(record.files)
    transaction.write(_tasks(change).doc.path, append_log(_tasks(change), _render(entry)))
    return Done(f'Accepted "{name}". Its items can now be applied.', commit(transaction))


def tick(
    start: Path,
    name: str,
    number: str,
    today: datetime.date,
    *,
    by: str | None = None,
) -> Done:
    """Tick an item: it has been applied. A ``(ticked)`` record says when, and who.

    The tick of an item the human does names the human; any other names the planner.
    """
    record, change, state = _open(start, name)
    _require_accepted(state)
    item = find_item(change, number)
    item_state = _item_state(state, number)
    if item.ticked:
        raise Refusal(f"Item {number} is already ticked.")
    if item_state.escalated or item.blocked:
        why = item_state.escalated or f"it is blocked: {item.blocked}"
        raise Refusal(
            f"Item {number} waits on the human: {why}. Once that is settled, run "
            f'"wm resolve {name} {number} "<what was decided>"".'
        )
    if item_state.redo:
        raise Refusal(
            f"A review asked for changes to item {number}. Reopen it first with "
            f'"wm reopen {name} {number}".'
        )
    who = _who(record, RecordKind.TICKED, by, human=item.build is BuildRole.HUMAN)
    line = _render(records.Record(RecordKind.TICKED, today, who=who, item=number))
    paths = _write_tasks(record, change, append_log(_tasks(change), line, tick=number))
    return Done(f"Ticked item {number} of {name}.", paths)


def _add_stopper(  # noqa: PLR0913 - the item, the stopper and who recorded it when
    start: Path,
    name: str,
    number: str,
    kind: RecordKind,
    text: str,
    *,
    today: datetime.date | None,
    by: str | None,
    details: Sequence[str] = (),
) -> Done:
    record, change, state = _open(start, name)
    _require_accepted(state)
    item = find_item(change, number)
    note = one_line(text, "a reason")
    listed = _details(details)
    if item.ticked:
        raise Refusal(f"Item {number} is already ticked, so there is nothing left to stop.")
    open_now = item.blocked if kind is RecordKind.BLOCKED else item.spec_gap
    if open_now is not None:
        raise Refusal(
            f'Item {number} already has an open "({kind.value})" record. Resolve it first '
            f'with "wm resolve {name} {number} "<what was decided>"".'
        )
    entry = records.Record(kind, _today(today), who=_who(record, kind, by), text=note, item=number)
    line = _render(entry)
    paths = _write_tasks(record, change, append_log(_tasks(change), line, details=listed))
    return Done(f'Wrote "{line}" to the Log of {name}.', paths)


def block(  # noqa: PLR0913 - the item, the reason, its details and who
    start: Path,
    name: str,
    number: str,
    reason: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record that an item is blocked, and why."""
    return _add_stopper(
        start, name, number, RecordKind.BLOCKED, reason, today=today, by=by, details=details
    )


def report_gap(  # noqa: PLR0913 - the item, what is missing, its details and who
    start: Path,
    name: str,
    number: str,
    note: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record that the record wasn't enough to build an item: a spec gap."""
    return _add_stopper(
        start, name, number, RecordKind.GAP, note, today=today, by=by, details=details
    )


def revise(  # noqa: PLR0913 - the reason, the parts it changed, its details and who
    start: Path,
    name: str,
    why: str,
    today: datetime.date | None = None,
    *,
    parts: Sequence[str] = (),
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record why an accepted change was edited, and which parts the edit changed."""
    record, change, state = _open(start, name)
    text = one_line(why, "why the change was revised")
    listed = _details(details)
    if change.acceptance is None:
        raise Refusal(
            f'The change "{name}" has never been accepted, so there is no acceptance to revise. '
            "Edit it, and the human accepts it once it is ready."
        )
    known = _revisable_parts(change)
    unknown = [part for part in parts if part not in known]
    if unknown:
        raise Refusal(
            f"{_part_names(unknown)} {'is' if len(unknown) == 1 else 'are'} not part of "
            f'"{name}". Name its items by number, "proposal", "design", or "specs/<area>" for '
            f"one of its deltas: {', '.join(sorted(known))}."
        )
    entry = records.Record(
        RecordKind.REVISED,
        _today(today),
        who=_who(record, RecordKind.REVISED, by),
        text=text,
        parts=tuple(dict.fromkeys(parts)) or None,
    )
    paths = _write_tasks(record, change, append_log(_tasks(change), _render(entry), details=listed))
    if state.acceptance is AcceptanceState.VALID:
        then = "The acceptance still holds, so the change goes on as it is."
    else:
        then = f'The human accepts it again with "wm accept {name}".'
    return Done(f'Recorded the revision of "{name}". {then}', paths)


def _revisable_parts(change: Change) -> set[str]:
    """The parts of a change a revision can name."""
    parts = {"proposal", *(f"specs/{area}" for area in change.deltas)}
    if change.design is not None:
        parts.add("design")
    if change.tasks is not None:
        parts.update(item.number for item in change.tasks.items)
    return parts


def _part_names(parts: Sequence[str]) -> str:
    """Parts as a message names them: an item by its number, anything else in quotes."""
    return ", ".join(f"Item {part}" if part[:1].isdigit() else f'"{part}"' for part in parts)


def _unrevised(change: Change) -> bool:
    """Whether the change was accepted before and no revision follows its last acceptance."""
    log = change.tasks.log if change.tasks else ()
    accepted = [index for index, entry in enumerate(log) if entry.kind is RecordKind.ACCEPTED]
    if not accepted:
        return False
    return not any(entry.kind is RecordKind.REVISED for entry in log[accepted[-1] + 1 :])


def add_note(  # noqa: PLR0913 - the item, the note, its details and who
    start: Path,
    name: str,
    number: str,
    note: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Write a note about an item that is still to be finished, such as a partial result, into
    the change's Log."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    item = find_item(change, number)
    text = one_line(note, "a note")
    listed = _details(details)
    if item.ticked:
        raise Refusal(f"Item {number} is already ticked, so there is nothing left to note.")
    entry = records.Record(
        RecordKind.NOTE,
        _today(today),
        who=_who(record, RecordKind.NOTE, by),
        text=text,
        item=number,
    )
    line = _render(entry)
    paths = _write_tasks(record, change, append_log(_tasks(change), line, details=listed))
    return Done(f'Wrote "{line}" to the Log of {name}. Item {number} is still to apply.', paths)


def _place_roots(record: Record) -> list[tuple[str, Path]]:
    """Where a finding's absolute path may point: the project, and each code repo here."""
    roots: list[tuple[str, Path]] = [("", record.project.root)]
    for name, location in repo_locations(record).items():
        if location.folder is not None:
            roots.append((name, location.folder))
    return roots


def _findings(record: Record, findings: Sequence[str]) -> tuple[list[str], bool]:
    """The findings as wm writes them, the place in backticks, and whether one is critical.

    A place's absolute path is written relative to the project, or as
    ``<repo>/<path>`` in an atlas code repo; any other absolute path is refused.
    """
    written: list[str] = []
    critical = False
    roots: list[tuple[str, Path]] | None = None
    for finding in findings:
        parsed = records.parse_finding_argument(one_line(finding, "a finding"))
        if parsed is None:
            raise Refusal(
                f'"{finding}" is not a finding. Write it as "{records.FINDING_ARGUMENT}", '
                'with the place in backticks when it holds ": ".'
            )
        if roots is None:
            roots = _place_roots(record)
        place = records.relative_place(parsed.place, roots)
        if place is None:
            raise Refusal(
                f'The place "{parsed.place}" is a path outside this project. Give the place '
                "relative to the project's top folder, such as src/limit.py:12, or in an atlas "
                "as <repo>/<path>."
            )
        parsed = records.Finding(parsed.severity, place, parsed.text)
        critical = critical or parsed.severity is ReviewSeverity.CRITICAL
        try:
            written.append(records.render_finding(parsed))
        except RecordError as error:
            raise Refusal(str(error)) from error
    return written, critical


def _require_reviewable(name: str, state: ChangeState) -> None:
    """A change is reviewed once every item is ticked and no verdict waits to be dealt with."""
    unticked = [item.number for item in state.items if not item.ticked]
    if unticked:
        raise Refusal(
            f'"{name}" can\'t be reviewed yet: {_listed(unticked)} not ticked. The change is '
            "reviewed as a whole once every item is built."
        )
    if state.review.reopen:
        raise Refusal(
            f'A review of "{name}" named {", ".join(state.review.reopen)} to rebuild. Reopen '
            f'and rebuild them first, starting with "wm reopen {name} {state.review.reopen[0]}".'
        )
    if state.review.escalated:
        raise Refusal(
            f'The review of "{name}" waits on the human: {state.review.escalated}. Once that is '
            f'settled, run "wm resolve {name} {REVIEW_TARGET} "<what was decided>"".'
        )


def self_review(  # noqa: PLR0913 - the summary, its findings and details, and who
    start: Path,
    name: str,
    summary: str,
    today: datetime.date,
    *,
    findings: Sequence[str] = (),
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record the planner's own review of the change, or of the items no review covers yet."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    text = one_line(summary, "a summary of the review")
    listed = _details(details)
    written, critical = _findings(record, findings)
    _require_reviewable(name, state)
    level = state.review.level
    if level is ReviewLevel.NONE:
        raise Refusal(f'"{name}" is at review level none and needs no review record.')
    if level is ReviewLevel.INDEPENDENT:
        raise Refusal(
            f'"{name}" needs an independent review, so a self-review doesn\'t count. Have a '
            "reviewer check it and record the verdict."
        )
    if state.review.reviewed:
        raise Refusal(f'"{name}" already has the review it needs.')
    if critical:
        raise Refusal(
            "A review with a critical finding can't count as done. Fix what it found and "
            f'review again, or name the items to rebuild with "wm verdict {name} changes".'
        )
    entry = records.Record(
        RecordKind.SELF_REVIEW,
        today,
        who=_who(record, RecordKind.SELF_REVIEW, by),
        text=text,
        covers=state.review.to_review,
    )
    new_text = append_log(_tasks(change), _render(entry), written, details=listed)
    paths = _write_tasks(record, change, new_text)
    return Done(f"Recorded the self-review of {name}.", paths)


def verdict(  # noqa: PLR0913 - the verdict, and the items and findings it names
    start: Path,
    name: str,
    result: Verdict,
    reasons: str,
    today: datetime.date,
    *,
    items: Sequence[str] = (),
    findings: Sequence[str] = (),
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record a reviewer's verdict on the change, or on the items no review covers yet."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    text = one_line(reasons, "the reviewer's reasons")
    listed = _details(details)
    written, critical = _findings(record, findings)
    for number in items:
        find_item(change, number)
    if result is Verdict.CHANGES and not items:
        raise Refusal(
            'A "changes" verdict names the items to rebuild, for example '
            f'"wm verdict {name} changes "<reasons>" --items 1.2 2.1".'
        )
    if result is not Verdict.CHANGES and items:
        raise Refusal(f'Only a "changes" verdict names items to rebuild, not "{result.value}".')
    if result is Verdict.PASS and critical:
        raise Refusal(
            'A "pass" can\'t come with a critical finding. Record "changes" with the items '
            "to rebuild, or leave the finding out if it isn't critical."
        )
    _require_reviewable(name, state)
    entry = records.Record(
        RecordKind.REVIEW,
        today,
        who=_who(record, RecordKind.REVIEW, by),
        verdict=result,
        items=tuple(dict.fromkeys(items)) or None,
        text=text,
        covers=state.review.to_review,
    )
    new_text = append_log(_tasks(change), _render(entry), written, details=listed)
    paths = _write_tasks(record, change, new_text)
    return Done(f"Recorded the verdict {result.value} on {name}.", paths)


def reopen(
    start: Path, name: str, number: str, today: datetime.date, *, by: str | None = None
) -> Done:
    """Reopen an item that a review named to rebuild."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    find_item(change, number)
    if number not in state.review.reopen:
        raise Refusal(
            f"No open review of {name} names item {number} to rebuild, so there is nothing "
            "to reopen."
        )
    line = _render(
        records.Record(
            RecordKind.REOPENED, today, who=_who(record, RecordKind.REOPENED, by), item=number
        )
    )
    text = append_log(_tasks(change), line, untick=number)
    paths = _write_tasks(record, change, text)
    return Done(
        f"Reopened item {number} of {name}. The change needs an independent review once it "
        "is rebuilt.",
        paths,
    )


def resolve(  # noqa: PLR0913 - what was decided, its details and who
    start: Path,
    name: str,
    target: str,
    decision: str,
    today: datetime.date,
    *,
    by: str | None = None,
    details: Sequence[str] = (),
) -> Done:
    """Record what the human decided about an item or the review, and free it.

    ``target`` is an item's number, or ``review`` for the change's review.
    """
    record, change, state = _open(start, name)
    text = one_line(decision, "what was decided")
    listed = _details(details)
    entry = records.Record(
        RecordKind.RESOLVED, today, who=_who(record, RecordKind.RESOLVED, by), text=text
    )
    line = _render(entry)
    item_line = _render(dataclasses.replace(entry, item=target))
    if target == REVIEW_TARGET:
        if not state.review.escalated:
            raise Refusal(
                f'Nothing about the review of "{name}" went to the human, so there is nothing '
                "to resolve."
            )
        paths = _write_tasks(record, change, append_log(_tasks(change), line, details=listed))
        return Done(f"Resolved the review of {name}. The change is reviewed again.", paths)
    item = find_item(change, target)
    item_state = _item_state(state, target)
    if not (item.blocked or item_state.escalated):
        raise Refusal(
            f"Item {target} isn't blocked and nothing about it went to the human, "
            f"so there is nothing to resolve. For the change's review, run \"wm resolve {name} "
            f'{REVIEW_TARGET} "<what was decided>"".'
        )
    new_text = append_log(_tasks(change), item_line, untick=target, details=listed)
    paths = _write_tasks(record, change, new_text)
    return Done(f"Resolved item {target} of {name}. It is ready to be applied again.", paths)


def _merge_specs(record: Record, change: Change, transaction: Transaction) -> dict[str, Spec]:
    """Stage every delta's merge; returns the specs as they will read afterwards."""
    specs = dict(record.specs)
    for domain in sorted(change.deltas):
        merged = merge_delta(record.specs.get(domain), change.deltas[domain])
        if merged.text is None:
            raise Refusal(f'The delta for "{domain}" doesn\'t merge: {merged.problems[0].message}')
        path = f"{SPECS}/{domain}.md"
        transaction.write(path, merged.text)
        specs[domain] = parse_spec(domain, Document.parse(path, merged.text))
    return specs


def sync(start: Path, name: str, today: datetime.date, *, by: str | None = None) -> Done:
    """Merge an applied change's deltas into the specs without archiving it.

    The change stays active and accepted: its acceptance is stamped again for
    the specs as they now read: the fingerprint goes on the ``(synced)`` record,
    which marks its deltas as merged, so the ``(accepted)`` record stays as written.
    """
    record, change, state = _open(start, name)
    if change.synced is not None:
        raise Refusal(f'The change "{name}" was already synced on {change.synced}.')
    if not state.applied:
        raise Refusal(
            f'Only an applied change can be synced, and "{name}" is {state.phase}. '
            f'Its next step is "{state.next_step.kind}". {state.next_step.reason}'.rstrip()
        )
    if not change.deltas:
        raise Refusal(f'The change "{name}" has no deltas, so there is nothing to sync.')
    assert change.proposal is not None
    assert change.acceptance is not None
    transaction = Transaction(record.files)
    specs = _merge_specs(record, change, transaction)
    accepted = change.acceptance
    fingerprint = change_fingerprint(change, specs, record.default_review, accepted.items)
    entry = records.Record(
        RecordKind.SYNCED, today, who=_who(record, RecordKind.SYNCED, by), fingerprint=fingerprint
    )
    transaction.write(_tasks(change).doc.path, append_log(_tasks(change), _render(entry)))
    domains = ", ".join(sorted(change.deltas))
    return Done(
        f'Synced "{name}" into the specs ({domains}). The change stays active.',
        commit(transaction),
    )


def _archive_gate(state: ChangeState, override: str | None) -> None:
    """The archive gate. Only missing review records can be overridden."""
    name = state.name
    if state.next_step.kind in _DRAFTING or state.acceptance is not AcceptanceState.VALID:
        raise Refusal(
            f'"{name}" can\'t be archived: it is not accepted as it stands (it is '
            f"{state.phase}). This can't be overridden; the human accepts it with "
            f'"wm accept {name}".'
        )
    blocking = [c for c in state.conflicts if c.kind is ConflictKind.MISMATCH]
    if blocking:
        raise Refusal(
            f'"{name}" can\'t be archived: it has a conflict. {blocking[0].message} '
            "This can't be overridden."
        )
    unticked = [item.number for item in state.items if not item.ticked]
    if unticked:
        raise Refusal(
            f'"{name}" can\'t be archived: {_listed(unticked)} not ticked. '
            "This can't be overridden; apply the items first."
        )
    unreviewed = not state.review.reviewed
    if unreviewed and override is None and state.review.uncovered:
        raise Refusal(
            f'"{name}" can\'t be archived: {_listed(list(state.review.uncovered))} not reviewed: '
            "no passing review covers them. Review them, or the human can archive anyway with "
            f'"wm archive {name} --override "<reason>"".'
        )
    if unreviewed and override is None:
        raise Refusal(
            f'"{name}" can\'t be archived: it is missing the {state.review.level} review of the '
            "change. Review the change, or the human can archive anyway with "
            f'"wm archive {name} --override "<reason>"".'
        )
    if override is not None and not unreviewed:
        raise Refusal(
            f'"{name}" has the review it needs, so there is nothing to override. '
            "Archive it without --override."
        )


def _listed(numbers: list[str]) -> str:
    if len(numbers) == 1:
        return f"item {numbers[0]} is"
    return f"items {', '.join(numbers)} are"


_OUTCOME_FORM = (
    f'"{label_line(BUILT, "<what was built>")}" and '
    f'"{label_line(DIFFERS, "<how it differs, or none>")}"'
)


def _values(given: str | Sequence[str] | None) -> list[str]:
    """--built or --differs as a list: given once, more than once, or not at all."""
    if given is None:
        return []
    return [given] if isinstance(given, str) else list(given)


def _outcome_line(label: str, values: Sequence[str], what: str) -> str:
    """One Outcome label: its value on the line, or several as nested bullets under it."""
    texts = [one_line(value, what) for value in values]
    if len(texts) == 1:
        return label_line(label, texts[0])
    return "\n".join([label_line(label), *(f"  - {text}" for text in texts)])


def _outcome(
    name: str,
    proposal: Proposal,
    built: str | Sequence[str] | None,
    differs: str | Sequence[str] | None,
) -> str:
    """The Outcome to write: from --built and --differs, or the one in the proposal."""
    built_values, differs_values = _values(built), _values(differs)
    if differs_values and not built_values:
        raise Refusal("--differs goes with --built. Pass both, or neither.")
    existing = proposal.outcome
    if built_values:
        if existing:
            raise Refusal(
                f'The proposal of "{name}" already has an outcome. Drop --built and --differs, '
                "or edit the outcome in the proposal."
            )
        return "\n".join(
            [
                _outcome_line(BUILT, built_values, "what was built"),
                _outcome_line(
                    DIFFERS, differs_values or [NONE], "how it differs from the proposal"
                ),
            ]
        )
    if not existing:
        raise Refusal(
            'Archiving records what came of the change. Pass --built "<what was built>" and, '
            'when it differs from the proposal, --differs "<how>".'
        )
    missing = [label for label in (BUILT, DIFFERS) if label not in proposal.outcome_lines]
    if missing:
        raise Refusal(
            f'The outcome in the proposal of "{name}" needs a "{label_line(missing[0])}" line. '
            f"An outcome is written {_OUTCOME_FORM}."
        )
    return existing


def _archive_explorations(
    record: Record, transaction: Transaction, today: datetime.date, folder: tuple[str, str]
) -> None:
    """Stage the move of each exploration whose work the staged operation finishes.

    Run after the links are rewritten: an active exploration whose ``led-to`` targets
    all point into an archive, as staged, moves to ``explorations/archive/<date>-<name>.md``.
    ``folder`` is the change or milestone folder the operation moves, as (source, target).
    """
    finished: list[Document] = []
    for name, exploration in sorted(record.explorations.items()):
        path = exploration.doc.path
        staged = transaction.staged(path)
        doc = Document.parse(path, staged) if staged is not None else exploration.doc
        if led_to_done(parse_exploration(name, doc)):
            finished.append(doc)
    _move_explorations(record, transaction, finished, today, folder)


def _move_explorations(
    record: Record,
    transaction: Transaction,
    moving: Sequence[Document],
    today: datetime.date,
    folder: tuple[str, str] | None = None,
) -> None:
    """Stage moving explorations, as given, to the archive, and re-aim every link they break.

    Each moves to ``explorations/archive/<date>-<name>.md``, with its own links
    re-aimed from there; links to it from the rest of the active record follow it.
    ``folder`` is a folder the same operation moves, as (source, target): its files'
    staged text is aimed from the target, so their links are read from there.
    A file already at a target refuses the operation, before anything is written.
    """
    if not moving:
        return
    moves: dict[str, str] = {}
    for doc in moving:
        name = doc.path.rsplit("/", 1)[-1].removesuffix(".md")
        target = f"{EXPLORATIONS}/{ARCHIVE}/{ArchiveName(today, name).folder}.md"
        if record.files.path(target).exists():
            raise Refusal(
                f'The exploration "{name}" would move to {target}, but an exploration of that '
                "name was already archived today. Nothing was changed; rename the exploration, "
                "then try again."
            )
        moves[doc.path] = target
    given = {doc.path: doc for doc in moving}
    for original in record.documents():
        staged = transaction.staged(original.path)
        if original.path in given:
            current = given[original.path]
        elif staged is not None:
            current = Document.parse(original.path, staged)
        else:
            current = original
        path, text = current.path, current.text
        if folder is not None and (path == folder[0] or path.startswith(f"{folder[0]}/")):
            path = folder[1] + path[len(folder[0]) :]
            current = Document.parse(path, text)
        for source, target in moves.items():
            text = rewrite_links(Document.parse(path, text), source, target)
            if path == source:
                path = target
        if path in moves.values():
            transaction.write(path, text)
            transaction.delete(original.path)
        elif text != current.text:
            transaction.write(original.path, text)


def drop_exploration(start: Path, name: str, reason: str, today: datetime.date) -> Done:
    """Drop an open exploration: write its status and reason, and move it to the archive."""
    record = open_record(start, writing=True)
    exploration = record.explorations.get(name)
    if exploration is None:
        known = ", ".join(sorted(record.explorations)) or "none"
        raise Refusal(f'There is no active exploration "{name}". Active explorations: {known}.')
    if exploration.status == LED_TO:
        raise Refusal(
            f'The exploration "{name}" led to a change or milestone, so it is not dropped: it '
            "ends when its work is archived, and wm archive or wm close moves it then."
        )
    if exploration.status != OPEN or exploration.status_index is None:
        raise Refusal(
            f'Only an open exploration is dropped. Give "{name}" the line '
            f'"{label_line(STATUS, OPEN)}" '
            "first, then drop it."
        )
    if not reason.strip():
        raise Refusal('Say why the exploration is dropped: --reason "<why>".')
    if not any(s.title.casefold() == "conclusion" for s in exploration.doc.sections(2)):
        raise Refusal(
            f'The exploration "{name}" has no "## Conclusion" section for the reason. Add the '
            "heading, then drop it."
        )
    text = with_dropped(exploration, reason.strip())
    transaction = Transaction(record.files)
    _move_explorations(record, transaction, [Document.parse(exploration.doc.path, text)], today)
    target = f"{EXPLORATIONS}/{ARCHIVE}/{ArchiveName(today, name).folder}.md"
    return Done(f'Dropped the exploration "{name}" as {target}.', commit(transaction))


def archive(  # noqa: PLR0913 - the outcome's two parts, the override and who
    start: Path,
    name: str,
    today: datetime.date,
    *,
    built: str | Sequence[str] | None = None,
    differs: str | Sequence[str] | None = None,
    override: str | None = None,
    by: str | None = None,
) -> Done:
    """Archive a change: merge its deltas, write its outcome, move it to the dated archive."""
    record, change, state = _open(start, name)
    reason = one_line(override, "a reason for the override") if override is not None else None
    _archive_gate(state, reason)
    assert change.proposal is not None

    final = _outcome(name, change.proposal, built, differs)
    override_line: str | None = None
    if reason is not None:
        entry = records.Record(
            RecordKind.OVERRIDE, today, who=_who(record, RecordKind.OVERRIDE, by), text=reason
        )
        override_line = _render(entry)

    source = change.path
    target = f"{CHANGES}/{ARCHIVE}/{ArchiveName(today, name).folder}"
    if record.files.entries(target):
        raise Refusal(
            f'A change named "{name}" was already archived today ({target}). '
            "Archive this one tomorrow, or rename it."
        )

    home = record.milestones.get(change.proposal.milestone or "")
    home_file = f"{home.path}/{MILESTONE_FILE}" if home is not None else None
    archiver = _who(record, RecordKind.ARCHIVED, by)
    archived_line = _render(records.Record(RecordKind.ARCHIVED, today, who=archiver, change=name))
    closing = _render(records.Record(RecordKind.ARCHIVED, today, who=archiver))

    transaction = Transaction(record.files)
    if change.synced is None:
        _merge_specs(record, change, transaction)
    transaction.write(change.proposal.doc.path, set_outcome(change.proposal, final))
    tasks = _tasks(change)
    if override_line is not None:
        text = append_log(tasks, override_line)
        tasks = parse_tasks(Document.parse(tasks.doc.path, text))
    transaction.write(tasks.doc.path, append_log(tasks, closing))
    for doc in record.documents():
        staged = transaction.staged(doc.path)
        current = Document.parse(doc.path, staged) if staged is not None else doc
        text = current.text
        if doc.path.endswith(f"/{MILESTONE_FILE}"):
            text = tick_roadmap_lines(current, source)
            current = Document.parse(doc.path, text)
        text = rewrite_links(current, source, target)
        if doc.path == home_file:
            text = append_milestone_log(Document.parse(doc.path, text), archived_line)
        if text != doc.text:
            transaction.write(doc.path, text)
    _archive_explorations(record, transaction, today, (source, target))
    transaction.move(source, target)
    paths = commit(transaction)
    return Done(f'Archived "{name}" as {target}. Its deltas are now part of the specs.', paths)


def close_milestone(start: Path, name: str, today: datetime.date) -> Done:
    """Close a milestone: move it to the dated archive and rewrite the links to it.

    Refused until every line on its roadmap links to an archived change: a change
    still active, one that can't be found, or a planned line that was never
    proposed keeps it open.
    """
    record = open_record(start, writing=True)
    milestone = record.milestones.get(name)
    if milestone is None:
        known = ", ".join(sorted(record.milestones)) or "none"
        raise Refusal(f'There is no open milestone "{name}". Open milestones: {known}.')
    lines = milestone_state(record, milestone).lines
    active = [line.change for line in lines if line.status is RoadmapStatus.ACTIVE]
    missing = [line.change for line in lines if line.status is RoadmapStatus.MISSING]
    planned = [line.text for line in lines if line.status is RoadmapStatus.PLANNED]
    if active:
        raise Refusal(
            f'The milestone "{name}" stays open: {", ".join(filter(None, active))} '
            "is still active. Archive it first."
        )
    if missing:
        raise Refusal(
            f'The milestone "{name}" stays open: its roadmap links to '
            f"{', '.join(filter(None, missing))}, which can't be found. Fix the link, or "
            f'drop the line with "wm roadmap drop {name} <change> --reason "<why>"".'
        )
    if planned:
        raise Refusal(
            f'The milestone "{name}" stays open: its roadmap has lines never proposed: '
            f"{'; '.join(planned)}. Propose each with "
            f'"wm new change <name> --milestone {name}", or drop it with '
            f'"wm roadmap drop {name} <change> --reason "<why>"".'
        )
    source = milestone.path
    target = f"{MILESTONES}/{ARCHIVE}/{ArchiveName(today, name).folder}"
    if record.files.entries(target):
        raise Refusal(
            f'A milestone named "{name}" was already closed today ({target}). '
            "Close this one tomorrow, or rename it."
        )
    transaction = Transaction(record.files)
    for doc in record.documents():
        text = rewrite_links(doc, source, target)
        if text != doc.text:
            transaction.write(doc.path, text)
    _archive_explorations(record, transaction, today, (source, target))
    transaction.move(source, target)
    paths = commit(transaction)
    return Done(f'Closed the milestone "{name}" as {target}.', paths)

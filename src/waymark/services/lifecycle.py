"""The lifecycle: accepting a change, recording evidence, syncing and archiving.

Every gate lives here. A refused command changes nothing and says what to do.
wm writes the evidence itself; these functions are the only way it gets written.
"""

import datetime
from collections.abc import Sequence
from pathlib import Path

from waymark.record import git, records
from waymark.record.changes import Change
from waymark.record.deltas import merge_delta
from waymark.record.edits import append_log, edit_item, set_outcome
from waymark.record.fingerprint import change_fingerprint
from waymark.record.milestones import ROADMAP_FILE
from waymark.record.moves import rewrite_links, tick_roadmap_lines
from waymark.record.names import ArchiveName
from waymark.record.record import ARCHIVE, CHANGES, MILESTONES, SPECS, Record
from waymark.record.records import RecordError, RecordKind
from waymark.record.specs import Spec, parse_spec
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    ConflictKind,
    ItemState,
    RoadmapStatus,
    StepKind,
    milestone_state,
)
from waymark.record.store import Transaction
from waymark.record.tasks import Tasks
from waymark.record.terms import ReviewLevel, ReviewSeverity, Verdict
from waymark.record.text import Document
from waymark.services.common import (
    Done,
    Refusal,
    commit,
    find_change,
    find_item,
    one_line,
    open_record,
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


def _who(record: Record, by: str | None) -> str | None:
    """Who writes a record: --by, else the git user, else nobody named."""
    try:
        return records.who_for(record.project.root, by)
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
    if by is not None:
        who: str | None = _who(record, by)
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


def tick(start: Path, name: str, number: str) -> Done:
    """Tick an item: it has been applied."""
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
    paths = _write_tasks(record, change, edit_item(_tasks(change), number, ticked=True))
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
) -> Done:
    record, change, state = _open(start, name)
    _require_accepted(state)
    item = find_item(change, number)
    note = one_line(text, "a reason")
    if item.ticked:
        raise Refusal(f"Item {number} is already ticked, so there is nothing left to stop.")
    open_now = item.blocked if kind is RecordKind.BLOCKED else item.spec_gap
    if open_now is not None:
        raise Refusal(
            f'Item {number} already has an open "({kind.value})" record. Resolve it first '
            f'with "wm resolve {name} {number} "<what was decided>"".'
        )
    entry = records.Record(kind, _today(today), who=_who(record, by), text=note)
    line = _render(entry)
    paths = _write_tasks(record, change, edit_item(_tasks(change), number, add=[line]))
    return Done(f'Wrote "{line}" under item {number} of {name}.', paths)


def block(
    start: Path,
    name: str,
    number: str,
    reason: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
) -> Done:
    """Record that an item is blocked, and why."""
    return _add_stopper(start, name, number, RecordKind.BLOCKED, reason, today=today, by=by)


def report_gap(
    start: Path,
    name: str,
    number: str,
    note: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
) -> Done:
    """Record that the record wasn't enough to build an item: a spec gap."""
    return _add_stopper(start, name, number, RecordKind.GAP, note, today=today, by=by)


def add_note(
    start: Path,
    name: str,
    number: str,
    note: str,
    today: datetime.date | None = None,
    *,
    by: str | None = None,
) -> Done:
    """Write a note under an item that is still to be finished, such as a partial result."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    item = find_item(change, number)
    text = one_line(note, "a note")
    if item.ticked:
        raise Refusal(f"Item {number} is already ticked, so there is nothing left to note.")
    entry = records.Record(RecordKind.NOTE, _today(today), who=_who(record, by), text=text)
    line = _render(entry)
    paths = _write_tasks(record, change, edit_item(_tasks(change), number, add=[line]))
    return Done(f'Wrote "{line}" under item {number} of {name}. It is still to apply.', paths)


def _findings(findings: Sequence[str]) -> tuple[list[str], bool]:
    """The findings as wm writes them, the place in backticks, and whether one is critical."""
    written: list[str] = []
    critical = False
    for finding in findings:
        parsed = records.parse_finding_argument(one_line(finding, "a finding"))
        if parsed is None:
            raise Refusal(
                f'"{finding}" is not a finding. Write it as "{records.FINDING_ARGUMENT}", '
                'with the place in backticks when it holds ": ".'
            )
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


def self_review(
    start: Path,
    name: str,
    summary: str,
    today: datetime.date,
    *,
    findings: Sequence[str] = (),
    by: str | None = None,
) -> Done:
    """Record the planner's own review of the whole change."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    text = one_line(summary, "a summary of the review")
    written, critical = _findings(findings)
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
    entry = records.Record(RecordKind.SELF_REVIEW, today, who=_who(record, by), text=text)
    new_text = append_log(_tasks(change), _render(entry), written)
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
) -> Done:
    """Record a reviewer's verdict on the whole change."""
    record, change, state = _open(start, name)
    _require_accepted(state)
    text = one_line(reasons, "the reviewer's reasons")
    written, critical = _findings(findings)
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
        who=_who(record, by),
        verdict=result,
        items=tuple(dict.fromkeys(items)) or None,
        text=text,
    )
    new_text = append_log(_tasks(change), _render(entry), written)
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
    line = _render(records.Record(RecordKind.REOPENED, today, who=_who(record, by)))
    text = edit_item(_tasks(change), number, ticked=False, add=[line])
    paths = _write_tasks(record, change, text)
    return Done(
        f"Reopened item {number} of {name}. The change needs an independent review once it "
        "is rebuilt.",
        paths,
    )


def resolve(
    start: Path,
    name: str,
    target: str,
    decision: str,
    today: datetime.date,
    *,
    by: str | None = None,
) -> Done:
    """Record what the human decided about an item or the review, and free it.

    ``target`` is an item's number, or ``review`` for the change's review.
    """
    record, change, state = _open(start, name)
    text = one_line(decision, "what was decided")
    entry = records.Record(RecordKind.RESOLVED, today, who=_who(record, by), text=text)
    line = _render(entry)
    if target == REVIEW_TARGET:
        if not state.review.escalated:
            raise Refusal(
                f'Nothing about the review of "{name}" went to the human, so there is nothing '
                "to resolve."
            )
        paths = _write_tasks(record, change, append_log(_tasks(change), line))
        return Done(f"Resolved the review of {name}. The change is reviewed again.", paths)
    item = find_item(change, target)
    item_state = _item_state(state, target)
    if not (item.blocked or item_state.escalated):
        raise Refusal(
            f"Item {target} isn't blocked and nothing about it went to the human, "
            f"so there is nothing to resolve. For the change's review, run \"wm resolve {name} "
            f'{REVIEW_TARGET} "<what was decided>"".'
        )
    new_text = edit_item(_tasks(change), target, ticked=False, add=[line])
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
    entry = records.Record(RecordKind.SYNCED, today, who=_who(record, by), fingerprint=fingerprint)
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


def archive(
    start: Path,
    name: str,
    today: datetime.date,
    *,
    outcome: str | None = None,
    override: str | None = None,
    by: str | None = None,
) -> Done:
    """Archive a change: merge its deltas, write its outcome, move it to the dated archive."""
    record, change, state = _open(start, name)
    reason = one_line(override, "a reason for the override") if override is not None else None
    _archive_gate(state, reason)
    assert change.proposal is not None

    existing = change.proposal.outcome
    given = outcome.strip() if outcome else ""
    if given and existing:
        raise Refusal(
            f'The proposal of "{name}" already has an outcome. Drop --outcome, or edit the '
            "outcome in the proposal."
        )
    final = given or existing
    if not final:
        raise Refusal(
            'Archiving records what came of the change. Pass --outcome "<what happened>", '
            'or write the "## Outcome" section in the proposal.'
        )
    override_line: str | None = None
    if reason is not None:
        entry = records.Record(RecordKind.OVERRIDE, today, who=_who(record, by), text=reason)
        override_line = _render(entry)

    source = change.path
    target = f"{CHANGES}/{ARCHIVE}/{ArchiveName(today, name).folder}"
    if record.files.entries(target):
        raise Refusal(
            f'A change named "{name}" was already archived today ({target}). '
            "Archive this one tomorrow, or rename it."
        )

    transaction = Transaction(record.files)
    if change.synced is None:
        _merge_specs(record, change, transaction)
    transaction.write(change.proposal.doc.path, set_outcome(change.proposal, final))
    if override_line is not None:
        transaction.write(_tasks(change).doc.path, append_log(_tasks(change), override_line))
    for doc in record.documents():
        staged = transaction.staged(doc.path)
        current = Document.parse(doc.path, staged) if staged is not None else doc
        text = current.text
        if doc.path.endswith(f"/{ROADMAP_FILE}"):
            text = tick_roadmap_lines(current, source)
            current = Document.parse(doc.path, text)
        text = rewrite_links(current, source, target)
        if text != doc.text:
            transaction.write(doc.path, text)
    transaction.move(source, target)
    paths = commit(transaction)
    return Done(f'Archived "{name}" as {target}. Its deltas are now part of the specs.', paths)


def close_milestone(start: Path, name: str, today: datetime.date) -> Done:
    """Close a milestone: move it to the dated archive and rewrite the links to it.

    Refused while a change its roadmap links to is still active or can't be
    found. Lines for changes that were never proposed don't block.
    """
    record = open_record(start, writing=True)
    milestone = record.milestones.get(name)
    if milestone is None:
        known = ", ".join(sorted(record.milestones)) or "none"
        raise Refusal(f'There is no open milestone "{name}". Open milestones: {known}.')
    lines = milestone_state(record, milestone).lines
    active = [line.change for line in lines if line.status is RoadmapStatus.ACTIVE]
    missing = [line.change for line in lines if line.status is RoadmapStatus.MISSING]
    if active:
        raise Refusal(
            f'The milestone "{name}" stays open: {", ".join(filter(None, active))} '
            "is still active. Archive it first, or take its line off the roadmap."
        )
    if missing:
        raise Refusal(
            f'The milestone "{name}" stays open: its roadmap links to '
            f"{', '.join(filter(None, missing))}, which can't be found. Fix the link, or "
            "take the line off the roadmap."
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
    transaction.move(source, target)
    paths = commit(transaction)
    dropped = [line.text for line in lines if line.status is RoadmapStatus.PLANNED]
    note = f" Never proposed: {'; '.join(dropped)}." if dropped else ""
    return Done(f'Closed the milestone "{name}" as {target}.{note}', paths)

"""Context packs: the excerpts of the record one job gets, and nothing else.

An implementer gets its item, the change's proposal, deltas and design, the
requirements those deltas touch, and the project's context and apply rules. A
reviewer gets the whole change: every item with its criteria and verification,
the deltas and their scenarios, the design, the earlier reviews of the change,
and the project's context and review rules; it does not get the notes left
while building, or the proposal.

Building a pack for an implementer or reviewer is also the delegation gate. An
implementer's pack is refused unless the change is accepted, the item has
criteria and the record around it has no problems. A reviewer's pack is refused
unless every item is ticked and the change needs an independent review it
doesn't have yet.
"""

from typing import Any

from waymark.record.atlas import Location
from waymark.record.changes import Change
from waymark.record.links import LinkChecker
from waymark.record.record import Record
from waymark.record.records import RecordKind
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    ConflictKind,
    ExplorationStatus,
    ItemState,
    derive_state,
)
from waymark.record.tasks import Item, ReviewRecord
from waymark.record.terms import Layout, ReviewLevel, Step
from waymark.record.text import Document
from waymark.services.common import Refusal, find_change, find_item, repo_locations, state_of
from waymark.services.references import reference_record

CONTEXT_VERSION = 1
DELEGATED_VERSION = 2
"""The version of the implementer's and reviewer's packs; 2 reviews the whole change."""
EXPLORE = "explore"
IMPLEMENT = "implement"
REVIEW = "review"
ROLES = (EXPLORE, IMPLEMENT, REVIEW)

RESULT_LINE = "RESULT: done | partial | spec-gap | blocked"
VERDICT_LINE = "VERDICT: pass | changes <item> <item>... | spec-gap"
FINDING_LINE = "FINDING: <critical | warning | suggestion>: <place>: <text>"

_ENDINGS = {
    IMPLEMENT: (
        f'End your reply with one line, "{RESULT_LINE}", followed by a short note. '
        "Use spec-gap when the record isn't enough to build the item; don't guess."
    ),
    REVIEW: (
        f'Give each finding on a line of its own, "{FINDING_LINE}". Then end your reply with '
        f'two lines: "CHANGE: <change>", then "{VERDICT_LINE}", followed by your reasons. '
        "A changes verdict names the items to rebuild; a pass has no critical finding. Use "
        "spec-gap when the record isn't enough to judge the change."
    ),
}


def _text(doc: Document) -> str:
    """A document's text with line feeds, whatever the file uses."""
    return "\n".join(line.text for line in doc.lines).strip("\n")


def _documents(change: Change) -> list[Document]:
    docs = [change.proposal.doc] if change.proposal else []
    docs += [delta.doc for _, delta in sorted(change.deltas.items())]
    docs += [change.design.doc] if change.design else []
    docs += [change.tasks.doc] if change.tasks else []
    return docs


def record_warnings(record: Record, change: Change, state: ChangeState) -> list[str]:
    """What is wrong in the record around a change: format problems, broken links, conflicts."""
    warnings = [f"{p.path}:{p.line}: {p.message}" for p in change.problems]
    checker = LinkChecker(record.project.record_root)
    for doc in _documents(change):
        warnings += [f"{p.path}:{p.line}: {p.message}" for p in checker.problems(doc)]
    warnings += [c.message for c in state.conflicts if c.kind is ConflictKind.MISMATCH]
    return warnings


def _acceptance_problem(state: ChangeState) -> str | None:
    if state.acceptance is AcceptanceState.MISSING:
        return (
            f'The change "{state.name}" is not accepted, so none of its items can be '
            f'delegated. The human accepts it with "wm accept {state.name}".'
        )
    if state.acceptance is AcceptanceState.WITHDRAWN:
        return (
            f'The acceptance of "{state.name}" was withdrawn, so none of its items can be '
            f'delegated. The human accepts it again with "wm accept {state.name}".'
        )
    return None


def _item_problem(name: str, item: Item, item_state: ItemState) -> str | None:
    """Why an implementer may not be started on an item; None when it may."""
    number = item.number
    resolve = f'"wm resolve {name} {number} "<what was decided>""'
    if item_state.escalated or (item.blocked and not item.ticked):
        why = item_state.escalated or f"it is blocked: {item.blocked}"
        return f"Item {number} waits on the human: {why}. Once that is settled, run {resolve}."
    if item_state.redo:
        return (
            f"A review asked for changes to item {number}. Reopen it first with "
            f'"wm reopen {name} {number}".'
        )
    if not item.criteria:
        return (
            f"Item {number} has no criteria, so there is nothing to build against. "
            'Add a "Criteria:" line under it; that edits the change, so it needs accepting again.'
        )
    if item.ticked:
        return f"Item {number} is already ticked. Pick an item that is still to apply."
    return None


def _review_problem(name: str, state: ChangeState) -> str | None:
    """Why a reviewer may not be started on a change; None when it may."""
    review = state.review
    unticked = [item.number for item in state.items if not item.ticked]
    if unticked:
        return (
            f"{name} has items still to build ({', '.join(unticked)}). The change is reviewed "
            "as a whole once every item is ticked."
        )
    if review.reopen:
        return (
            f"A review of {name} named {', '.join(review.reopen)} to rebuild. Reopen and "
            f'rebuild them first, starting with "wm reopen {name} {review.reopen[0]}".'
        )
    if review.escalated:
        return (
            f"The review of {name} waits on the human: {review.escalated}. Once that is "
            f'settled, run "wm resolve {name} review "<what was decided>"".'
        )
    if review.reviewed:
        return f"{name} already has the review it needs."
    if review.level is not ReviewLevel.INDEPENDENT:
        return (
            f"{name} is reviewed at level {review.level}, so no reviewer is started. "
            f'The planner records the review with "wm review {name} --self".'
        )
    return None


def item_location(record: Record, item: Item) -> Location | None:
    """Where the code repo an item names is on this machine; None when it names none."""
    if record.layout is not Layout.ATLAS or not item.repo:
        return None
    return repo_locations(record).get(item.repo)


def delegation_problems(record: Record, change: Change, item: Item | None, role: str) -> list[str]:
    """Why an implementer may not be started on an item, or a reviewer on the change.

    Empty when it may. A reviewer takes no item.
    """
    state = state_of(record, change)
    first = _acceptance_problem(state)
    if first is None and role == REVIEW:
        first = _review_problem(change.name, state)
    elif first is None and item is not None:
        item_state = next(i for i in state.items if i.number == item.number)
        first = _item_problem(change.name, item, item_state)
    if first:
        return [first]
    warnings = record_warnings(record, change, state)
    location = item_location(record, item) if item is not None else None
    if location is not None and location.folder is None:
        warnings.append(f"Item {item.number} works in a repo that isn't here. {location.detail}")  # type: ignore[union-attr]
    return warnings


def _review(record: ReviewRecord) -> dict[str, Any]:
    return {
        "date": record.date.isoformat(),
        "verdict": record.verdict.value if record.verdict else None,
        "text": record.text,
        "items": list(record.items),
        "findings": [
            {"severity": f.severity.value, "place": f.place, "text": f.text}
            for f in record.findings
        ],
    }


def _definition(item: Item, location: Location | None) -> dict[str, Any]:
    """An item's definition: what to build and how to check it, with where its repo is."""
    return {
        "number": item.number,
        "title": item.title,
        "criteria": item.criteria,
        "verify": item.verify,
        "repo": item.repo,
        "repo_found": None if location is None else location.folder is not None,
        "_local": {"repo_folder": str(location.folder) if location and location.folder else None},
    }


def _item(record: Record, change: Change, item: Item) -> dict[str, Any]:
    """An implementer's item: its definition, its notes, and the reviews that named it."""
    records = change.tasks.review_records if change.tasks else ()
    return {
        **_definition(item, item_location(record, item)),
        "notes": list(item.notes),
        "reviews": [_review(r) for r in records if item.number in r.items],
        "resolutions": [r.text for r in item.records if r.kind is RecordKind.RESOLVED],
    }


def _deltas(change: Change) -> list[dict[str, Any]]:
    return [
        {"spec": domain, "text": _text(delta.doc)}
        for domain, delta in sorted(change.deltas.items())
    ]


def _touched_requirements(record: Record, change: Change) -> list[dict[str, Any]]:
    """The living text of every requirement the change modifies or removes."""
    touched: list[dict[str, Any]] = []
    for domain, delta in sorted(change.deltas.items()):
        spec = record.specs.get(domain)
        names = [r.name for r in delta.modified] + [r.name for r in delta.removed]
        for name in names:
            living = spec.requirement(name) if spec else None
            if living is not None:
                touched.append(
                    {"spec": domain, "name": living.name, "text": "\n".join(living.block)}
                )
    return touched


def _refuse(role: str, target: str, problems: list[str]) -> None:
    if problems:
        more = f" ({len(problems) - 1} more; see wm check)" if len(problems) > 1 else ""
        raise Refusal(f"No {role} context pack for {target}: {problems[0]}{more}")


def _implement_pack(record: Record, change_name: str, number: str) -> dict[str, Any]:
    change = find_change(record, change_name)
    item = find_item(change, number)
    _refuse(
        IMPLEMENT, f"{change_name} {number}", delegation_problems(record, change, item, IMPLEMENT)
    )
    charter = record.charter
    proposal = change.proposal
    return {
        "schema": f"wm.context.{IMPLEMENT}",
        "version": DELEGATED_VERSION,
        "for": IMPLEMENT,
        "change": change.name,
        "item": _item(record, change, item),
        "context": charter.context if charter else "",
        "rules": charter.rules.get(Step.APPLY, "") if charter else "",
        "proposal": dict(proposal.sections) if proposal else None,
        "deltas": _deltas(change),
        "requirements": _touched_requirements(record, change),
        "design": _text(change.design.doc) if change.design else None,
        "ends_with": _ENDINGS[IMPLEMENT],
    }


def _review_pack(record: Record, change_name: str) -> dict[str, Any]:
    change = find_change(record, change_name)
    _refuse(REVIEW, change_name, delegation_problems(record, change, None, REVIEW))
    state = state_of(record, change)
    charter = record.charter
    tasks = change.tasks
    records = tasks.review_records if tasks else ()
    return {
        "schema": f"wm.context.{REVIEW}",
        "version": DELEGATED_VERSION,
        "for": REVIEW,
        "change": change.name,
        "review_level": state.review.level.value,
        "items": [
            _definition(item, item_location(record, item))
            for item in (tasks.items if tasks else ())
        ],
        "reviews": [_review(r) for r in records if r.kind is RecordKind.REVIEW],
        "resolutions": [r.text for r in records if r.kind is RecordKind.RESOLVED],
        "context": charter.context if charter else "",
        "rules": charter.rules.get(Step.REVIEW, "") if charter else "",
        "deltas": _deltas(change),
        "design": _text(change.design.doc) if change.design else None,
        "ends_with": _ENDINGS[REVIEW],
    }


def _references(record: Record) -> list[dict[str, Any]]:
    """An index of every referenced atlas's specs. Their text is fetched on request."""
    index: list[dict[str, Any]] = []
    for reference in record.config.references if record.config else ():
        try:
            other = reference_record(record, reference.atlas)
        except Refusal:
            index.append({"atlas": reference.atlas, "found": False, "specs": []})
            continue
        specs = [
            {"name": name, "title": spec.title, "purpose": spec.purpose}
            for name, spec in sorted(other.specs.items())
        ]
        index.append({"atlas": reference.atlas, "found": True, "specs": specs})
    return index


def _explore_pack(record: Record) -> dict[str, Any]:
    state = derive_state(record)
    charter = record.charter
    return {
        "schema": "wm.context.explore",
        "version": CONTEXT_VERSION,
        "for": EXPLORE,
        "charter": dict(charter.sections) if charter else {},
        "rules": charter.rules.get(Step.EXPLORE, "") if charter else "",
        "specs": [
            {
                "name": name,
                "title": spec.title,
                "purpose": spec.purpose,
                "requirements": [requirement.name for requirement in spec.requirements],
            }
            for name, spec in sorted(record.specs.items())
        ],
        "changes": [
            {
                "name": name,
                "title": change.proposal.title if change.proposal else "",
                "phase": state.changes[name].phase.value,
            }
            for name, change in sorted(record.changes.items())
        ],
        "milestones": [
            {"name": name, "archived": milestone.archived, "total": milestone.total}
            for name, milestone in sorted(state.milestones.items())
        ],
        "explorations": [
            {
                "name": name,
                "title": record.explorations[name].title,
                "status": exploration.status.value,
                "detail": exploration.detail
                if exploration.status is not ExplorationStatus.UNREADABLE
                else None,
            }
            for name, exploration in sorted(state.explorations.items())
        ],
        "references": _references(record),
    }


def context_pack(
    record: Record, role: str, change_name: str | None = None, number: str | None = None
) -> dict[str, Any]:
    """The context pack for one job. For an implementer or reviewer this is the delegation gate."""
    if role == EXPLORE:
        if change_name or number:
            raise Refusal("An explore context pack takes no change or item.")
        return _explore_pack(record)
    if role == REVIEW:
        if not change_name or number:
            raise Refusal(
                "A context pack for review names exactly one change and no item: "
                "wm context <change> --for review"
            )
        return _review_pack(record, change_name)
    if not change_name or not number:
        raise Refusal(
            f"A context pack for {role} names exactly one change and one item: "
            f"wm context <change> <item> --for {role}"
        )
    return _implement_pack(record, change_name, number)

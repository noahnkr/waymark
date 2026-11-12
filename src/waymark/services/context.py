"""Context packs: the excerpts of the record one job gets, and nothing else.

An implementer gets its item, the change's proposal, deltas and design, the
requirements those deltas touch, and the project's context and apply rules. A
reviewer gets the item with its criteria and verification, the deltas and
their scenarios, and the project's context and review rules; it does not get
the implementer's notes, the proposal or the design.

Building a pack for an implementer or reviewer is also the delegation gate:
it is refused unless the change is accepted, the item has criteria and the
record around it has no problems.
"""

from typing import Any

from waymark.record.changes import Change
from waymark.record.links import LinkChecker
from waymark.record.record import Record
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    ConflictKind,
    ExplorationStatus,
    ItemState,
    derive_state,
)
from waymark.record.tasks import Item, RecordKind
from waymark.record.terms import ReviewLevel, Step
from waymark.record.text import Document
from waymark.services.common import Refusal, find_change, find_item, state_of

CONTEXT_VERSION = 1
EXPLORE = "explore"
IMPLEMENT = "implement"
REVIEW = "review"
ROLES = (EXPLORE, IMPLEMENT, REVIEW)

RESULT_LINE = "RESULT: done | partial | spec-gap | blocked"
VERDICT_LINE = "VERDICT: pass | changes | spec-gap"

_ENDINGS = {
    IMPLEMENT: (
        f'End your reply with one line, "{RESULT_LINE}", followed by a short note. '
        "Use spec-gap when the record isn't enough to build the item; don't guess."
    ),
    REVIEW: (
        f'End your reply with one line, "{VERDICT_LINE}", followed by your reasons. '
        "Use spec-gap when the record isn't enough to judge the item."
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


def _item_problem(  # noqa: PLR0911 - one return per reason an item can't be delegated
    name: str, item: Item, item_state: ItemState, role: str
) -> str | None:
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
            f"Item {number} has no criteria, so there is nothing to build or review against. "
            'Add a "Criteria:" line under it; that edits the change, so it needs accepting again.'
        )
    if role == IMPLEMENT and item.ticked:
        return f"Item {number} is already ticked. Pick an item that is still to apply."
    if role == REVIEW and not item.ticked:
        return f"Item {number} isn't ticked yet, so there is nothing to review."
    if role == REVIEW and item_state.level is ReviewLevel.NONE:
        return f"Item {number} is at review level none and needs no review."
    if role == REVIEW and item_state.reviewed:
        return f"Item {number} already has the review record it needs."
    return None


def delegation_problems(record: Record, change: Change, item: Item, role: str) -> list[str]:
    """Why an implementer or reviewer may not be started on an item; empty when it may."""
    state = state_of(record, change)
    item_state = next(i for i in state.items if i.number == item.number)
    first = _acceptance_problem(state) or _item_problem(change.name, item, item_state, role)
    if first:
        return [first]
    return record_warnings(record, change, state)


def _item(item: Item, item_state: ItemState, role: str) -> dict[str, Any]:
    reviews = [
        {
            "date": r.date.isoformat(),
            "verdict": r.verdict.value if r.verdict else None,
            "text": r.text,
        }
        for r in item.records
        if r.kind is RecordKind.REVIEW
    ]
    resolutions = [r.text for r in item.records if r.kind is RecordKind.RESOLVED]
    return {
        "number": item.number,
        "title": item.title,
        "criteria": item.criteria,
        "verify": item.verify,
        "repo": item.repo,
        "review_level": item_state.level.value,
        "notes": list(item.notes) if role == IMPLEMENT else [],
        "reviews": reviews,
        "resolutions": resolutions,
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


def _delegated_pack(record: Record, role: str, change_name: str, number: str) -> dict[str, Any]:
    change = find_change(record, change_name)
    item = find_item(change, number)
    problems = delegation_problems(record, change, item, role)
    if problems:
        more = f" ({len(problems) - 1} more; see wm check)" if len(problems) > 1 else ""
        raise Refusal(f"No {role} context pack for {change_name} {number}: {problems[0]}{more}")
    state = state_of(record, change)
    item_state = next(i for i in state.items if i.number == item.number)
    charter = record.charter
    step = Step.APPLY if role == IMPLEMENT else Step.REVIEW
    implementing = role == IMPLEMENT
    proposal = change.proposal
    return {
        "schema": f"wm.context.{role}",
        "version": CONTEXT_VERSION,
        "for": role,
        "change": change.name,
        "item": _item(item, item_state, role),
        "context": charter.context if charter else "",
        "rules": charter.rules.get(step, "") if charter else "",
        "proposal": dict(proposal.sections) if proposal and implementing else None,
        "deltas": _deltas(change),
        "requirements": _touched_requirements(record, change) if implementing else [],
        "design": _text(change.design.doc) if change.design and implementing else None,
        "ends_with": _ENDINGS[role],
    }


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
    }


def context_pack(
    record: Record, role: str, change_name: str | None = None, number: str | None = None
) -> dict[str, Any]:
    """The context pack for one job. For an implementer or reviewer this is the delegation gate."""
    if role == EXPLORE:
        if change_name or number:
            raise Refusal("An explore context pack takes no change or item.")
        return _explore_pack(record)
    if not change_name or not number:
        raise Refusal(
            f"A context pack for {role} names exactly one change and one item: "
            f"wm context <change> <item> --for {role}"
        )
    return _delegated_pack(record, role, change_name, number)

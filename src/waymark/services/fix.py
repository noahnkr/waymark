"""``wm check --fix``: bring the record to its standard layout when the human asks.

It covers the charter, the specs, the active changes, the milestones and the
explorations, never the archive. It changes layout only (``record/layout.py``),
never wording. Before anything is written it checks, on the fixed text, that
every task list keeps its records and ticks and every active change keeps its
acceptance state; a difference would be a fault in wm, so the fix is refused
and nothing is written. Every file is written, or none.
"""

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from waymark.record.artifacts.changes import Change
from waymark.record.artifacts.deltas import parse_delta
from waymark.record.artifacts.design import parse_design
from waymark.record.artifacts.proposal import parse_proposal
from waymark.record.artifacts.specs import Spec, parse_spec
from waymark.record.artifacts.tasks import parse_tasks
from waymark.record.evidence.evidence import evidence
from waymark.record.evidence.fingerprint import change_fingerprint
from waymark.record.markdown.text import Document
from waymark.record.record import Record
from waymark.record.state import AcceptanceState, acceptance_state
from waymark.record.writing.layout import Fix, standard_layout
from waymark.record.writing.store import Transaction
from waymark.services.common import Refusal, commit, open_record

_FAULT = (
    "The layout fix would change {what}, which a fix never does. This is a fault in wm; "
    "nothing was changed. Please report it."
)


@dataclass(frozen=True)
class FixedFile:
    """A file the fix rewrote, relative to the record's root, and the kinds of fix it took."""

    path: str
    fixes: tuple[Fix, ...]


def fix_layout(start: Path) -> tuple[FixedFile, ...]:
    """Rewrite the active record in its standard layout; returns what was fixed."""
    record = open_record(start, writing=True)
    staged: dict[str, str] = {}
    fixed: list[FixedFile] = []
    for doc in record.documents():
        text, fixes = standard_layout(doc.text)
        if fixes:
            staged[doc.path] = text
            fixed.append(FixedFile(doc.path, fixes))
    if not staged:
        return ()
    _guard(record, staged)
    transaction = Transaction(record.files)
    for path, text in staged.items():
        transaction.write(path, text)
    commit(transaction)
    return tuple(fixed)


def _doc(doc: Document, staged: Mapping[str, str]) -> Document:
    text = staged.get(doc.path)
    return doc if text is None else Document.parse(doc.path, text)


def _fixed_change(change: Change, staged: Mapping[str, str]) -> Change:
    """The change as it reads with the fixed text."""
    proposal = change.proposal
    design = change.design
    tasks = change.tasks
    return dataclasses.replace(
        change,
        proposal=parse_proposal(_doc(proposal.doc, staged)) if proposal else None,
        design=parse_design(_doc(design.doc, staged)) if design else None,
        tasks=parse_tasks(_doc(tasks.doc, staged)) if tasks else None,
        deltas={
            domain: parse_delta(domain, _doc(delta.doc, staged))
            for domain, delta in change.deltas.items()
        },
    )


def _accepted_after(
    record: Record, change: Change, specs: Mapping[str, Spec], staged: Mapping[str, str]
) -> AcceptanceState:
    after = _fixed_change(change, staged)
    acceptance = after.acceptance
    if acceptance is None:
        return AcceptanceState.MISSING
    current = change_fingerprint(after, specs, record.default_review, acceptance.items)
    return AcceptanceState.VALID if current == acceptance.fingerprint else AcceptanceState.WITHDRAWN


def _guard(record: Record, staged: Mapping[str, str]) -> None:
    """Refuse a fix that would change any record, tick or acceptance state."""
    for change in record.changes.values():
        if change.tasks is None:
            continue
        doc = change.tasks.doc
        if evidence(doc.path, doc.text) != evidence(doc.path, staged.get(doc.path, doc.text)):
            raise Refusal(_FAULT.format(what=f"the records or ticks in {doc.path}"))
    specs = {
        domain: parse_spec(domain, _doc(spec.doc, staged)) for domain, spec in record.specs.items()
    }
    for name, change in record.changes.items():
        before = acceptance_state(record, change)
        if _accepted_after(record, change, specs, staged) is not before:
            raise Refusal(_FAULT.format(what=f'the acceptance of "{name}"'))

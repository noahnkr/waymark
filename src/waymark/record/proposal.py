"""Proposals: why a change is wanted and what it changes, plus its owner, path and review level.

The acceptance and the sync are records in the task list's Log; an
``Accepted:``, ``Synced:`` or ``Review override:`` line here is from format 1.
"""

import datetime
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import (
    OLD_LAYOUT,
    collect_sections,
    content,
    parse_facts,
    require_title,
)
from waymark.record.problems import Problem
from waymark.record.terms import ReviewLevel
from waymark.record.text import Document

OWNER = "Owner"
ACCEPTED = "Accepted"
PATH = "Path"
SYNCED = "Synced"
REVIEW = "Review"
SHORT = "short"
FULL = "full"

WHY = "Why"
WHAT_CHANGES = "What changes"
NON_GOALS = "Non-goals"
IMPACT = "Impact"
OUTCOME = "Outcome"
REQUIRED_SECTIONS = (WHY, WHAT_CHANGES, NON_GOALS, IMPACT)

NO_SPEC_CHANGES = "No spec changes"


@dataclass(frozen=True)
class Acceptance:
    """An acceptance: when, by whom, the fingerprint of what was accepted, and its items.

    ``index`` is the line of its record in the task list.
    """

    date: datetime.date
    who: str
    fingerprint: str
    index: int
    items: tuple[str, ...]


@dataclass(frozen=True)
class Proposal:
    """A change's proposal."""

    doc: Document
    title: str
    owner: str | None
    short_path: bool
    review: ReviewLevel | None
    sections: Mapping[str, str]
    no_spec_changes: bool
    outcome: str | None
    problems: tuple[Problem, ...]

    def accepted_text(self) -> str:
        """The text acceptance covers: everything but the outcome."""
        skipped: set[int] = set()
        for section in self.doc.sections(2):
            if section.title.casefold() == OUTCOME.casefold():
                skipped.update(range(section.start, section.end))
        lines = self.doc.lines
        kept = [line.text for index, line in enumerate(lines) if index not in skipped]
        while kept and not kept[-1].strip():
            kept.pop()
        return "\n".join(kept)


def parse_proposal(doc: Document) -> Proposal:
    """Read a proposal."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    facts = parse_facts(doc, {OWNER, PATH, REVIEW}, problems, prose=True)
    problems.extend(
        Problem(doc.path, fact.index + 1, "old-layout", OLD_LAYOUT)
        for fact in facts.values()
        if not fact.bullet
    )

    owner = facts[OWNER].value if OWNER in facts else ""
    if not owner:
        problems.append(
            Problem(
                doc.path,
                1,
                "missing-owner",
                f'Every change has one owner. Add an "{OWNER}: <name>" line under the title.',
            )
        )

    short_path = False
    if PATH in facts:
        value = facts[PATH].value
        short_path = value == SHORT
        if value not in (SHORT, FULL):
            problems.append(
                Problem(
                    doc.path,
                    facts[PATH].index + 1,
                    "invalid-path",
                    f'"{PATH}:" is "{SHORT}" for the short path or "{FULL}". '
                    "Fix the value, or remove the line for the full path.",
                )
            )

    review: ReviewLevel | None = None
    if REVIEW in facts:
        value = facts[REVIEW].value
        if value in set(ReviewLevel):
            review = ReviewLevel(value)
        else:
            levels = ", ".join(level.value for level in ReviewLevel)
            problems.append(
                Problem(
                    doc.path,
                    facts[REVIEW].index + 1,
                    "invalid-review-level",
                    f'"{REVIEW}:" is one of {levels}. Fix the value, or remove the line for '
                    "the project's default.",
                )
            )

    found = collect_sections(doc, REQUIRED_SECTIONS, problems, optional=(OUTCOME,))
    sections = {name: content(doc, found, name, problems) for name in REQUIRED_SECTIONS}
    outcome = doc.body(found[OUTCOME]) if OUTCOME in found else None
    return Proposal(
        doc=doc,
        title=title,
        owner=owner or None,
        short_path=short_path,
        review=review,
        sections=sections,
        no_spec_changes=NO_SPEC_CHANGES.casefold() in sections[IMPACT].casefold(),
        outcome=outcome or None,
        problems=tuple(problems),
    )

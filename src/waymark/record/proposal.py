"""Proposals: why a change is wanted and what it changes, plus its owner, path and review level.

The acceptance and the sync are records in the task list's Log.
"""

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import (
    collect_sections,
    content,
    parse_facts,
    require_title,
)
from waymark.record.problems import Problem
from waymark.record.terms import ReviewLevel
from waymark.record.text import Document

OWNER = "Owner"
PATH = "Path"
REVIEW = "Review"
SHORT = "short"
FULL = "full"

WHY = "Why"
WHAT_CHANGES = "What changes"
NON_GOALS = "Non-goals"
IMPACT = "Impact"
OUTCOME = "Outcome"
REQUIRED_SECTIONS = (WHY, WHAT_CHANGES, NON_GOALS, IMPACT)

SPECS = "Specs"
USER_VISIBLE = "User-visible"
CODE = "Code"
IMPACT_LINES = (SPECS, USER_VISIBLE, CODE)
NONE = "none"
BUILT = "Built"
DIFFERS = "Differs"

_OUTCOME_LINE = re.compile(r"^[-*][ \t]+(Built|Differs):(?:[ \t]+(.*))?$")

_IMPACT_LINE = re.compile(r"^[-*][ \t]+(Specs|User-visible|Code):(?:[ \t]+(.*))?$")
_SPEC_NAME = re.compile(r"`([^`\s]+)`")


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
    impact: Mapping[str, str]
    """The Impact's labeled lines: ``Specs``, ``User-visible`` and ``Code``, as written."""
    impact_specs: tuple[str, ...] | None
    """The specs named under ``Specs:``; empty for ``none``; None without the line, or when
    it neither says ``none`` nor names a spec in backticks."""
    outcome: str | None
    problems: tuple[Problem, ...]

    @property
    def no_spec_changes(self) -> bool:
        """Whether the Impact says ``- Specs: none``."""
        return self.impact_specs == ()

    @property
    def outcome_lines(self) -> dict[str, str]:
        """The Outcome's ``Built`` and ``Differs`` lines that have text."""
        found: dict[str, str] = {}
        for line in (self.outcome or "").split("\n"):
            match = _OUTCOME_LINE.match(line)
            if match and (match.group(2) or "").strip():
                found.setdefault(match.group(1), match.group(2).strip())
        return found

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
    every_fact = parse_facts(doc, {OWNER, PATH, REVIEW}, problems, prose=True)
    facts = {key: fact for key, fact in every_fact.items() if fact.bullet}

    owner = facts[OWNER].value if OWNER in facts else ""
    if not owner:
        problems.append(
            Problem(
                doc.path,
                1,
                "missing-owner",
                f'Every change has one owner. Add a "- {OWNER}: <name>" line under the title.',
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
    impact = (
        _impact_lines(doc, found[IMPACT].body_start, found[IMPACT].end) if IMPACT in found else {}
    )
    impact_specs: tuple[str, ...] | None = None
    if SPECS in impact:
        text = impact[SPECS]
        names = tuple(_SPEC_NAME.findall(text))
        impact_specs = () if text.casefold() == NONE else names or None
    return Proposal(
        doc=doc,
        title=title,
        owner=owner or None,
        short_path=short_path,
        review=review,
        sections=sections,
        impact=impact,
        impact_specs=impact_specs,
        outcome=outcome or None,
        problems=tuple(problems),
    )


def _impact_lines(doc: Document, start: int, end: int) -> dict[str, str]:
    """The Impact's labeled lines, each with the bullets indented under it."""
    lines: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_comment = False
    for index in range(start, end):
        line = doc.lines[index]
        text = line.text
        if in_comment or text.lstrip().startswith("<!--"):
            in_comment = "-->" not in text
            continue
        if line.is_blank or line.in_fence:
            continue
        if text.startswith((" ", "\t")):
            if current is not None:
                current.append(text.strip())
            continue
        match = _IMPACT_LINE.match(text)
        current = None
        if match and match.group(1) not in lines:
            current = lines[match.group(1)] = [match.group(2) or ""]
    return {
        label: "\n".join(part for part in parts if part).strip() for label, parts in lines.items()
    }

"""Proposals: why a change is wanted and what it changes, plus its owner and acceptance."""

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, content, parse_facts, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

OWNER = "Owner"
ACCEPTED = "Accepted"
PATH = "Path"
SHORT = "short"
FULL = "full"

WHY = "Why"
WHAT_CHANGES = "What changes"
NON_GOALS = "Non-goals"
IMPACT = "Impact"
OUTCOME = "Outcome"
REQUIRED_SECTIONS = (WHY, WHAT_CHANGES, NON_GOALS, IMPACT)

NO_SPEC_CHANGES = "No spec changes"

_ACCEPTANCE = re.compile(r"^(\d{4}-\d{2}-\d{2}) by (\S.*?) \(fingerprint: ([0-9a-f]{16})\)$")


@dataclass(frozen=True)
class Acceptance:
    """The acceptance line: when, by whom, and the fingerprint of what was accepted."""

    date: datetime.date
    who: str
    fingerprint: str
    index: int


@dataclass(frozen=True)
class Proposal:
    """A change's proposal."""

    doc: Document
    title: str
    owner: str | None
    short_path: bool
    acceptance: Acceptance | None
    sections: Mapping[str, str]
    no_spec_changes: bool
    outcome: str | None
    problems: tuple[Problem, ...]

    def accepted_text(self) -> str:
        """The text acceptance covers: everything but the acceptance line and the outcome."""
        skipped: set[int] = set()
        facts = parse_facts(self.doc, {ACCEPTED}, [], prose=True)
        if ACCEPTED in facts:
            skipped.add(facts[ACCEPTED].index)
        for section in self.doc.sections(2):
            if section.title.casefold() == OUTCOME.casefold():
                skipped.update(range(section.start, section.end))
        lines = self.doc.lines
        kept = [line.text for index, line in enumerate(lines) if index not in skipped]
        while kept and not kept[-1].strip():
            kept.pop()
        return "\n".join(kept)


def format_acceptance(date: datetime.date, who: str, fingerprint: str) -> str:
    """The acceptance line as wm writes it."""
    return f"{ACCEPTED}: {date.isoformat()} by {who} (fingerprint: {fingerprint})"


def _parse_acceptance(
    doc: Document, value: str, index: int, problems: list[Problem]
) -> Acceptance | None:
    match = _ACCEPTANCE.match(value)
    date: datetime.date | None = None
    if match:
        try:
            date = datetime.date.fromisoformat(match.group(1))
        except ValueError:
            date = None
    if match is None or date is None:
        problems.append(
            Problem(
                doc.path,
                index + 1,
                "malformed-evidence",
                f'The "{ACCEPTED}:" line doesn\'t follow the format. It is written by wm; '
                "remove the line and accept the change again.",
            )
        )
        return None
    return Acceptance(date, match.group(2).strip(), match.group(3), index)


def parse_proposal(doc: Document) -> Proposal:
    """Read a proposal."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    facts = parse_facts(doc, {OWNER, ACCEPTED, PATH}, problems, prose=True)

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

    acceptance: Acceptance | None = None
    if ACCEPTED in facts:
        fact = facts[ACCEPTED]
        acceptance = _parse_acceptance(doc, fact.value, fact.index, problems)

    found = collect_sections(doc, REQUIRED_SECTIONS, problems, optional=(OUTCOME,))
    sections = {name: content(doc, found, name, problems) for name in REQUIRED_SECTIONS}
    outcome = doc.body(found[OUTCOME]) if OUTCOME in found else None
    return Proposal(
        doc=doc,
        title=title,
        owner=owner or None,
        short_path=short_path,
        acceptance=acceptance,
        sections=sections,
        no_spec_changes=NO_SPEC_CHANGES.casefold() in sections[IMPACT].casefold(),
        outcome=outcome or None,
        problems=tuple(problems),
    )

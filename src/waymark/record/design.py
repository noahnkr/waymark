"""Designs: how a change will be built, and the decisions it makes."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, content, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

CONTEXT = "Context"
APPROACH = "Approach"
DECISIONS = "Decisions"
RISKS = "Risks and trade-offs"
REQUIRED_SECTIONS = (CONTEXT, APPROACH, DECISIONS, RISKS)
DECISION_PARTS = ("Options", "Choice", "Why")

_DECISION = re.compile(r"^Decision:\s*(\S.*)$")
_PART = re.compile(r"^\s*(?:[-*]\s+)?(Options|Choice|Why):")


@dataclass(frozen=True)
class Decision:
    """One decision: the options, the choice and why."""

    name: str
    text: str
    index: int


@dataclass(frozen=True)
class Design:
    """A change's design."""

    doc: Document
    title: str
    sections: Mapping[str, str]
    decisions: tuple[Decision, ...]
    problems: tuple[Problem, ...]


def parse_design(doc: Document) -> Design:
    """Read a design."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: content(doc, found, name, problems) for name in REQUIRED_SECTIONS}

    decisions: list[Decision] = []
    if DECISIONS in found:
        parent = found[DECISIONS]
        for section in doc.sections(3, parent.body_start, parent.end):
            match = _DECISION.match(section.title)
            if match is None:
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "decision-format",
                        f'"{section.title}" is not a decision heading. '
                        'Write it as "Decision: <name>".',
                    )
                )
                continue
            lines = doc.lines[section.body_start : section.end]
            parts = {m.group(1) for line in lines if (m := _PART.match(line.text))}
            missing = [part for part in DECISION_PARTS if part not in parts]
            if missing:
                wanted = ", ".join(f'"{part}:"' for part in missing)
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "decision-incomplete",
                        f'Decision "{match.group(1).strip()}" gives the options, the choice and '
                        f"why. Add a line starting with {wanted}.",
                    )
                )
            decisions.append(Decision(match.group(1).strip(), doc.body(section), section.start))
    return Design(doc, title, sections, tuple(decisions), tuple(problems))

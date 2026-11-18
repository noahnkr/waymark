"""Designs: how a change will be built, and the decisions it makes."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.markdown.outline import collect_sections, content, require_title
from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import Document

CONTEXT = "Context"
APPROACH = "Approach"
DECISIONS = "Decisions"
RISKS = "Risks and trade-offs"
OPEN_QUESTIONS = "Open questions"
REQUIRED_SECTIONS = (CONTEXT, APPROACH, DECISIONS, RISKS)
DECISION_PARTS = ("Options", "Choice", "Why")
STATUS = "Status"
DECIDED_BY = "Decided by"
PROPOSED = "proposed"
DECIDED = "decided"
STATUSES = (PROPOSED, DECIDED)
DECIDERS = ("human", "planner")
NO_QUESTIONS = "None."

_DECISION = re.compile(r"^Decision:\s*(\S.*)$")
_PART = re.compile(r"^\s*(?:[-*]\s+)?(Options|Choice|Why|Status|Decided by):[ \t]*(.*)$")
_OPTION_SPLIT = re.compile(r";|\bor\b")
_LIST_ITEM = re.compile(r"^(?:[-*]|\d+\.)[ \t]+(\S.*)$")


@dataclass(frozen=True)
class Decision:
    """One decision: the options, the choice and why."""

    name: str
    text: str
    index: int
    status: str | None = None
    """The ``Status:`` value as written; None without the line."""
    decided_by: str | None = None
    """The ``Decided by:`` value as written; None without the line."""
    options: tuple[str, ...] = ()
    """The options: the bullets under ``- Options:``, or else the line split on ";" and "or"."""


@dataclass(frozen=True)
class Design:
    """A change's design."""

    doc: Document
    title: str
    sections: Mapping[str, str]
    decisions: tuple[Decision, ...]
    problems: tuple[Problem, ...]
    open_questions: tuple[str, ...] | None = None
    """The questions listed under ``## Open questions``; None without the section."""
    open_questions_index: int | None = None
    """The line of the ``## Open questions`` heading."""
    open_questions_prose: tuple[int, ...] = ()
    """Lines under ``## Open questions`` that are neither a list item nor ``None.``."""

    @property
    def unsettled(self) -> list[str]:
        """What keeps the design from acceptance: proposed decisions and open questions."""
        found = [f'decision "{d.name}" is proposed' for d in self.decisions if d.status == PROPOSED]
        found += [f'open question "{q}" is listed' for q in self.open_questions or ()]
        return found


def parse_design(doc: Document) -> Design:
    """Read a design."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems, optional=(OPEN_QUESTIONS,))
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
            values: dict[str, str] = {}
            bullets: list[str] = []
            in_options = False
            for line in lines:
                if m := _PART.match(line.text):
                    values.setdefault(m.group(1), m.group(2).strip())
                    in_options = m.group(1) == "Options"
                elif in_options and line.text.startswith((" ", "\t")):
                    if bullet := _LIST_ITEM.match(line.text.strip()):
                        bullets.append(bullet.group(1).strip())
                elif not line.is_blank:
                    in_options = False
            parts = set(values)
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
            decisions.append(
                Decision(
                    match.group(1).strip(),
                    doc.body(section),
                    section.start,
                    values.get(STATUS),
                    values.get(DECIDED_BY),
                    tuple(bullets) or _inline_options(values.get("Options", "")),
                )
            )
    questions: tuple[str, ...] | None = None
    prose: list[int] = []
    heading: int | None = None
    if OPEN_QUESTIONS in found:
        heading = found[OPEN_QUESTIONS].start
        questions, prose = _open_questions(
            doc, found[OPEN_QUESTIONS].body_start, found[OPEN_QUESTIONS].end
        )
    return Design(
        doc, title, sections, tuple(decisions), tuple(problems), questions, heading, tuple(prose)
    )


def _open_questions(doc: Document, start: int, end: int) -> tuple[tuple[str, ...], list[int]]:
    """The questions listed in a section, and the lines that are neither a question nor None."""
    questions: list[str] = []
    prose: list[int] = []
    in_comment = False
    for index in range(start, end):
        line = doc.lines[index]
        text = line.text.strip()
        if in_comment or text.startswith("<!--"):
            in_comment = "-->" not in text
            continue
        if line.is_blank or line.in_fence or line.text.startswith((" ", "\t")):
            continue
        if text == NO_QUESTIONS:
            continue
        if match := _LIST_ITEM.match(text):
            questions.append(match.group(1).strip())
        else:
            prose.append(index)
    return tuple(questions), prose


def _inline_options(text: str) -> tuple[str, ...]:
    """The options named on one line, split on ";" and on the word "or"."""
    parts = (part.strip().rstrip(",").strip() for part in _OPTION_SPLIT.split(text))
    return tuple(part for part in parts if part)

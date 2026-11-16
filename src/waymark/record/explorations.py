"""Explorations: saved thinking on a topic, whose conclusion says where it went."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import Fact, collect_sections, parse_facts, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

CONTEXT = "Context"
QUESTIONS = "Questions"
APPROACHES = "Approaches"
CONCLUSION = "Conclusion"
RELATED = "Related"
REQUIRED_SECTIONS = (CONTEXT, QUESTIONS, APPROACHES, CONCLUSION, RELATED)

_PARKED = re.compile(r"^Parked:\s*(.*)$")
STATUS = "Status"
OPEN = "open"
PARKED = "parked"
LED_TO = "led-to"
_STATUS = re.compile(r"^(open|parked|led-to)(?:\s+(\S.*))?$")


@dataclass(frozen=True)
class Exploration:
    """A saved exploration.

    ``parked`` is the reason from a ``Parked:`` conclusion. ``conclusion_links``
    are the link targets in the conclusion, in order.
    """

    name: str
    doc: Document
    title: str
    sections: Mapping[str, str]
    conclusion: str
    parked: str | None
    conclusion_links: tuple[str, ...]
    problems: tuple[Problem, ...]
    status: str | None = None
    """The ``- Status:`` value: open, parked or led-to; None when there is no line."""
    status_links: tuple[str, ...] = ()
    """The link targets on a ``led-to`` status line."""


def parse_exploration(name: str, doc: Document) -> Exploration:
    """Read an exploration."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: doc.body(found[name]) if name in found else "" for name in REQUIRED_SECTIONS}

    facts = parse_facts(doc, {STATUS}, problems, prose=True)
    status, status_links = _status(doc, facts.get(STATUS), problems)
    conclusion = sections[CONCLUSION]
    parked: str | None = None
    links: tuple[str, ...] = ()
    if CONCLUSION in found:
        section = found[CONCLUSION]
        links = tuple(
            link.target for link in doc.links() if section.body_start <= link.index < section.end
        )
        match = _PARKED.match(conclusion)
        if status == PARKED:
            parked = match.group(1).strip() if match else conclusion
            if not parked:
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "parked-without-reason",
                        "A parked exploration says why. Write the reason in the Conclusion.",
                    )
                )
        elif match:
            parked = match.group(1).strip()
            if not parked:
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "parked-without-reason",
                        'A parked exploration says why. Write "Parked: <reason>".',
                    )
                )
    return Exploration(
        name,
        doc,
        title,
        sections,
        conclusion,
        parked,
        links,
        tuple(problems),
        status,
        status_links,
    )


def _status(
    doc: Document, fact: Fact | None, problems: list[Problem]
) -> tuple[str | None, tuple[str, ...]]:
    """The exploration's status and, for ``led-to``, the links on its line."""
    if fact is None:
        return None, ()
    match = _STATUS.match(fact.value)
    if match is None:
        problems.append(
            Problem(
                doc.path,
                fact.index + 1,
                "unknown-status",
                f'"{fact.value}" is not a status. Write "- Status: open", "- Status: parked" '
                'or "- Status: led-to <link>".',
            )
        )
        return None, ()
    status = match.group(1)
    links = tuple(link.target for link in doc.links() if link.index == fact.index)
    if status == LED_TO and not links:
        problems.append(
            Problem(
                doc.path,
                fact.index + 1,
                "unknown-status",
                'A "led-to" status links to the change or milestone it led to.',
            )
        )
    return status, links

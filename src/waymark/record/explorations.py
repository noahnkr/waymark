"""Explorations: saved thinking on a topic, whose conclusion says where it went."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

CONTEXT = "Context"
QUESTIONS = "Questions"
APPROACHES = "Approaches"
CONCLUSION = "Conclusion"
RELATED = "Related"
REQUIRED_SECTIONS = (CONTEXT, QUESTIONS, APPROACHES, CONCLUSION, RELATED)

_PARKED = re.compile(r"^Parked:\s*(.*)$")


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


def parse_exploration(name: str, doc: Document) -> Exploration:
    """Read an exploration."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: doc.body(found[name]) if name in found else "" for name in REQUIRED_SECTIONS}

    conclusion = sections[CONCLUSION]
    parked: str | None = None
    links: tuple[str, ...] = ()
    if CONCLUSION in found:
        section = found[CONCLUSION]
        links = tuple(
            link.target for link in doc.links() if section.body_start <= link.index < section.end
        )
        match = _PARKED.match(conclusion)
        if match:
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
    return Exploration(name, doc, title, sections, conclusion, parked, links, tuple(problems))

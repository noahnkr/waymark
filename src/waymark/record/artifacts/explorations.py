"""Explorations: saved thinking on a topic, whose conclusion says where it went."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.markdown.outline import (
    Fact,
    collect_sections,
    parse_facts,
    require_title,
)
from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import BOM, Document

CONTEXT = "Context"
QUESTIONS = "Questions"
APPROACHES = "Approaches"
CONCLUSION = "Conclusion"
RELATED = "Related"
REQUIRED_SECTIONS = (CONTEXT, QUESTIONS, APPROACHES, CONCLUSION, RELATED)

STATUS = "Status"
OPEN = "open"
LED_TO = "led-to"
DROPPED = "dropped"
STATUSES = (OPEN, LED_TO, DROPPED)
_STATUS = re.compile(r"^(open|led-to|dropped)(?:\s+(\S.*))?$")
_FORMS = '"- Status: open", "- Status: led-to <link>" or "- Status: dropped"'


@dataclass(frozen=True)
class Exploration:
    """A saved exploration.

    ``conclusion_links`` are the link targets in the conclusion, in order.
    """

    name: str
    doc: Document
    title: str
    sections: Mapping[str, str]
    conclusion: str
    conclusion_links: tuple[str, ...]
    problems: tuple[Problem, ...]
    status: str | None = None
    """The ``- Status:`` value: open, led-to or dropped; None when there is no line."""
    status_links: tuple[str, ...] = ()
    """The link targets on a ``led-to`` status line."""
    status_index: int | None = None
    """The index of the ``- Status:`` line; None when there is no line."""


def parse_exploration(name: str, doc: Document) -> Exploration:
    """Read an exploration."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: doc.body(found[name]) if name in found else "" for name in REQUIRED_SECTIONS}

    facts = parse_facts(doc, {STATUS}, problems, prose=True)
    status, status_links = _status(doc, facts.get(STATUS), problems)
    conclusion = sections[CONCLUSION]
    links: tuple[str, ...] = ()
    if CONCLUSION in found:
        section = found[CONCLUSION]
        links = tuple(
            link.target for link in doc.links() if section.body_start <= link.index < section.end
        )
    return Exploration(
        name,
        doc,
        title,
        sections,
        conclusion,
        links,
        tuple(problems),
        status,
        status_links,
        facts[STATUS].index if STATUS in facts else None,
    )


def _join(doc: Document, lines: list[str], endings: list[str]) -> str:
    body = "".join(text + ending for text, ending in zip(lines, endings, strict=True))
    return (BOM if doc.bom else "") + body


def with_led_to(exploration: Exploration, name: str, target: str) -> str:
    """The exploration's text with its status led to ``name`` as well, line endings kept.

    An exploration that already led somewhere keeps its links, and the new one is
    added at the end of the line. Only the status line changes.
    """
    doc = exploration.doc
    assert exploration.status_index is not None
    lines = [line.text for line in doc.lines]
    endings = [line.ending for line in doc.lines]
    link = f"[{name}]({target})"
    at = exploration.status_index
    if exploration.status == LED_TO:
        lines[at] = f"{lines[at].rstrip()}, {link}"
    else:
        lines[at] = f"- {STATUS}: {LED_TO} {link}"
    return _join(doc, lines, endings)


def with_dropped(exploration: Exploration, reason: str) -> str:
    """The exploration's text with its status dropped and the reason ending its Conclusion."""
    doc = exploration.doc
    assert exploration.status_index is not None
    newline = doc.newline
    lines = [line.text for line in doc.lines]
    endings = [line.ending for line in doc.lines]
    lines[exploration.status_index] = f"- {STATUS}: {DROPPED}"
    section = next(s for s in doc.sections(2) if s.title.casefold() == CONCLUSION.casefold())
    filled = [i for i in range(section.body_start, section.end) if lines[i].strip()]
    at = filled[-1] + 1 if filled else section.body_start
    added = ["", reason]
    if at < len(lines) and lines[at].strip():
        added.append("")  # the next heading follows directly: keep a blank line before it
    if at > 0 and not endings[at - 1]:
        endings[at - 1] = newline
    lines[at:at] = added
    endings[at:at] = [newline] * len(added)
    return _join(doc, lines, endings)


def _status(
    doc: Document, fact: Fact | None, problems: list[Problem]
) -> tuple[str | None, tuple[str, ...]]:
    """The exploration's status and, for ``led-to``, the links on its line."""
    if fact is None:
        problems.append(
            Problem(
                doc.path,
                1,
                "missing-status",
                f"An exploration says where it stands in a line under its title: {_FORMS}.",
            )
        )
        return None, ()
    match = _STATUS.match(fact.value)
    if match is None:
        problems.append(
            Problem(
                doc.path,
                fact.index + 1,
                "unknown-status",
                f'"{fact.value}" is not a status. Write {_FORMS}.',
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

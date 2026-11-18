"""The charter: what the project is, and the context and rules every agent gets."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

CHARTER_FILE = "charter.md"

VISION = "Vision"
GOALS = "Goals"
NON_GOALS = "Non-goals"
CONSTRAINTS = "Constraints"
GLOSSARY = "Glossary"
CONTEXT = "Context"
RULES = "Rules"
REQUIRED_SECTIONS = (VISION, GOALS, NON_GOALS, CONSTRAINTS, GLOSSARY, CONTEXT, RULES)

GLOSSARY_LINE = re.compile(r"^- \*\*(\S[^*]*?)\*\*: \S")
"""A glossary entry: ``- **<term>**: <meaning>``."""

_NUMBERED_LINE = re.compile(r"^(\d+)\.[ \t]+\S")
"""An item of a numbered list: ``<n>. <text>``."""


@dataclass(frozen=True)
class Charter:
    """The project's charter.

    ``context`` and ``rules`` go to every agent at every step. ``rules`` is the
    numbered list under ``## Rules``, whole.
    """

    doc: Document
    title: str
    sections: Mapping[str, str]
    context: str
    rules: str
    problems: tuple[Problem, ...]


def parse_charter(doc: Document) -> Charter:
    """Read the charter. Sections may be empty while the charter is still a skeleton."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: doc.body(found[name]) if name in found else "" for name in REQUIRED_SECTIONS}

    if GLOSSARY in found:
        _check_glossary(doc, found[GLOSSARY].body_start, found[GLOSSARY].end, problems)
    for name in (GOALS, CONSTRAINTS, RULES):
        if name in found:
            _check_numbered(doc, name, found[name].body_start, found[name].end, problems)
    return Charter(doc, title, sections, sections[CONTEXT], sections[RULES], tuple(problems))


def _check_numbered(
    doc: Document, name: str, start: int, end: int, problems: list[Problem]
) -> None:
    """A numbered list, ``1. <text>``, counting from 1; indented lines continue an item."""
    expected = 1
    in_comment = False
    for index in range(start, end):
        line = doc.lines[index]
        text = line.text.strip()
        if in_comment or text.startswith("<!--"):
            in_comment = "-->" not in text
            continue
        if line.is_blank or line.in_fence or line.text.startswith((" ", "\t")):
            continue
        match = _NUMBERED_LINE.match(text)
        if match and int(match.group(1)) == expected:
            expected += 1
            continue
        problems.append(
            Problem(
                doc.path,
                index + 1,
                "numbered-list-format",
                f'{name} are a numbered list, one per line, such as "1. <text>". '
                f'This line should read "{expected}. <text>".',
            )
        )
        if match:
            expected = int(match.group(1)) + 1


def _check_glossary(doc: Document, start: int, end: int, problems: list[Problem]) -> None:
    """Every glossary line is an entry: ``- **<term>**: <meaning>``."""
    in_comment = False
    for index in range(start, end):
        line = doc.lines[index]
        text = line.text.strip()
        if in_comment or text.startswith("<!--"):
            in_comment = "-->" not in text
            continue
        if line.is_blank or line.in_fence or line.text.startswith(" "):
            continue
        if GLOSSARY_LINE.match(text):
            continue
        problems.append(
            Problem(
                doc.path,
                index + 1,
                "glossary-format",
                'A glossary entry is written "- **<term>**: <meaning>", one per line.',
            )
        )

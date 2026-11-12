"""Shared reading of an artifact's outline: its title, fact lines and named sections."""

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from waymark.record.problems import Problem
from waymark.record.text import Document, Section

_FACT = re.compile(r"^([A-Z][A-Za-z-]*):(?:[ \t]+(.*))?$")


@dataclass(frozen=True)
class Fact:
    """A plain ``Key: value`` line under an artifact's title."""

    value: str
    index: int


def require_title(doc: Document, problems: list[Problem]) -> str:
    """The document's title; reports a problem when there is none."""
    title = doc.title
    if title is None or not title.title:
        problems.append(
            Problem(doc.path, 1, "missing-title", 'Start the file with a "# <title>" heading.')
        )
        return ""
    return title.title


def parse_facts(
    doc: Document, keys: Collection[str], problems: list[Problem], *, prose: bool
) -> dict[str, Fact]:
    """Read the fact lines between the title and the first section.

    With ``prose`` false, any other text there is a problem.
    """
    facts: dict[str, Fact] = {}
    start, end = doc.preamble
    for index in range(start, end):
        line = doc.lines[index]
        if line.is_blank or line.text.lstrip().startswith("<!--"):
            continue
        match = _FACT.match(line.text)
        if match and match.group(1) in keys:
            key = match.group(1)
            if key in facts:
                problems.append(
                    Problem(
                        doc.path,
                        index + 1,
                        "duplicate-fact",
                        f'"{key}:" appears twice. Keep one line.',
                    )
                )
            else:
                facts[key] = Fact((match.group(2) or "").strip(), index)
        elif not prose:
            allowed = ", ".join(f'"{key}:"' for key in sorted(keys)) or "nothing"
            problems.append(
                Problem(
                    doc.path,
                    index + 1,
                    "unexpected-text",
                    f"Only {allowed} may appear between the title and the first section. "
                    "Move this text into a section.",
                )
            )
    return facts


def collect_sections(
    doc: Document,
    required: Sequence[str],
    problems: list[Problem],
    *,
    optional: Sequence[str] = (),
    strict: bool = False,
) -> dict[str, Section]:
    """Find the level-2 sections by name, ignoring case.

    Reports missing and duplicate sections and, when ``strict``, unknown ones.
    """
    wanted = {name.casefold(): name for name in (*required, *optional)}
    found: dict[str, Section] = {}
    for section in doc.sections(2):
        name = wanted.get(section.title.casefold())
        if name is None:
            if strict:
                expected = ", ".join(f'"{known}"' for known in wanted.values())
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "unknown-section",
                        f'"{section.title}" is not a section of this file. '
                        f"Use {expected}, or remove it.",
                    )
                )
        elif name in found:
            problems.append(
                Problem(
                    doc.path,
                    section.start + 1,
                    "duplicate-section",
                    f'"## {name}" appears twice. Merge the two sections.',
                )
            )
        else:
            found[name] = section
    problems.extend(
        Problem(doc.path, 1, "missing-section", f'Add a "## {name}" section.')
        for name in required
        if name not in found
    )
    return found


def content(doc: Document, sections: dict[str, Section], name: str, problems: list[Problem]) -> str:
    """A named section's text; an empty section is reported as a problem."""
    section = sections.get(name)
    if section is None:
        return ""
    text = doc.body(section)
    if not text:
        problems.append(
            Problem(
                doc.path,
                section.start + 1,
                "empty-section",
                f'"## {name}" is empty. Write its content.',
            )
        )
    return text


def split_names(value: str) -> tuple[str, ...]:
    """Split a comma-separated list of names."""
    return tuple(part.strip() for part in value.split(",") if part.strip())

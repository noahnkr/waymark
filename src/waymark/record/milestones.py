"""Milestones: a goal several changes work toward, and the roadmap that lists them, in one file."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, content, require_title
from waymark.record.problems import WHOLE_FILE, Problem
from waymark.record.text import BOM, Document

MILESTONE_FILE = "milestone.md"

GOAL = "Goal"
DONE_WHEN = "Done when"
NON_GOALS = "Non-goals"
ROADMAP = "Roadmap"
REQUIRED_SECTIONS = (GOAL, DONE_WHEN, NON_GOALS)

_ENTRY = re.compile(r"^\s*[-*]\s+(?:\[([ xX])\]\s+)?(\S.*)$")


@dataclass(frozen=True)
class Goal:
    """A milestone's aim."""

    doc: Document
    title: str
    sections: Mapping[str, str]
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class RoadmapEntry:
    """One roadmap line: a link to a change, or a plain line for one not proposed yet."""

    text: str
    target: str | None
    checked: bool
    index: int


@dataclass(frozen=True)
class Roadmap:
    """The changes a milestone expects."""

    doc: Document
    entries: tuple[RoadmapEntry, ...]
    problems: tuple[Problem, ...]


@dataclass(frozen=True)
class Milestone:
    """A milestone folder: its goal and its roadmap, both read from ``milestone.md``."""

    name: str
    path: str
    goal: Goal | None
    roadmap: Roadmap | None
    problems: tuple[Problem, ...]


def parse_milestone(doc: Document) -> tuple[Goal, Roadmap]:
    """Read ``milestone.md``: its goal sections, and the roadmap entries under ``## Roadmap``."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, (*REQUIRED_SECTIONS, ROADMAP), problems)
    sections = {name: content(doc, found, name, problems) for name in REQUIRED_SECTIONS}
    present = [name for name in (*REQUIRED_SECTIONS, ROADMAP) if name in found]
    if [found[name].start for name in present] != sorted(found[name].start for name in present):
        order = ", ".join(f'"## {name}"' for name in (*REQUIRED_SECTIONS, ROADMAP))
        problems.append(
            Problem(
                doc.path,
                WHOLE_FILE,
                "section-order",
                f"A milestone's sections come in the order {order}.",
            )
        )
    entries: list[RoadmapEntry] = []
    if ROADMAP in found:
        section = found[ROADMAP]
        targets: dict[int, str] = {}
        for link in doc.links():
            targets.setdefault(link.index, link.target)
        in_comment = False
        for index in range(section.body_start, section.end):
            line = doc.lines[index]
            if in_comment or line.text.lstrip().startswith("<!--"):
                in_comment = "-->" not in line.text
                continue
            match = None if line.in_fence else _ENTRY.match(line.text)
            if match:
                checked = match.group(1) is not None and match.group(1) != " "
                entries.append(
                    RoadmapEntry(match.group(2).strip(), targets.get(index), checked, index)
                )
    all_problems = tuple(problems)
    return Goal(doc, title, sections, all_problems), Roadmap(doc, tuple(entries), ())


def roadmap_lines(doc: Document) -> range:
    """The lines of a milestone's ``## Roadmap`` section; empty when it has none."""
    section = next((s for s in doc.sections(2) if s.title.casefold() == ROADMAP.casefold()), None)
    return range(section.body_start, section.end) if section else range(0)


def link_change(doc: Document, name: str, target: str) -> str:
    """The milestone's text with the change linked from its roadmap, line endings kept.

    The first roadmap line that links nowhere and is the change's name, or starts with
    ``<name>:``, becomes a link to ``target`` and keeps the rest of its text. Otherwise a
    line linking the change is added at the end of the roadmap, which is created when
    the milestone has none.
    """
    newline = doc.newline
    link = f"[{name}]({target})"
    lines = [line.text for line in doc.lines]
    endings = [line.ending for line in doc.lines]
    _, roadmap = parse_milestone(doc)
    planned = next(
        (
            entry
            for entry in roadmap.entries
            if entry.target is None and (entry.text == name or entry.text.startswith(f"{name}:"))
        ),
        None,
    )
    if planned is not None:
        text = lines[planned.index]
        at = text.index(planned.text)
        lines[planned.index] = text[:at] + link + text[at + len(name) :]
    else:
        section = next(
            (s for s in doc.sections(2) if s.title.casefold() == ROADMAP.casefold()), None
        )
        if section is None:
            added, at = ["", f"## {ROADMAP}", "", f"- {link}"], len(lines)
        else:
            filled = [i for i in range(section.start + 1, section.end) if lines[i].strip()]
            gap = section.start + 1 < section.end and not lines[section.start + 1].strip()
            if filled:
                at, added = filled[-1] + 1, [f"- {link}"]
            elif gap:
                at, added = section.start + 2, [f"- {link}"]
            else:
                at, added = section.start + 1, ["", f"- {link}"]
        if at > 0 and not endings[at - 1]:
            endings[at - 1] = newline
        lines[at:at] = added
        endings[at:at] = [newline] * len(added)
    body = "".join(text + ending for text, ending in zip(lines, endings, strict=True))
    return (BOM if doc.bom else "") + body

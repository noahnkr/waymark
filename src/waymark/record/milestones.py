"""Milestones: a goal several changes work toward, and the roadmap that lists them."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, content, require_title
from waymark.record.problems import Problem
from waymark.record.text import Document

GOAL_FILE = "goal.md"
ROADMAP_FILE = "roadmap.md"

GOAL = "Goal"
DONE_WHEN = "Done when"
NON_GOALS = "Non-goals"
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
    """A milestone folder: its goal and its roadmap."""

    name: str
    path: str
    goal: Goal | None
    roadmap: Roadmap | None
    problems: tuple[Problem, ...]


def parse_goal(doc: Document) -> Goal:
    """Read a milestone's goal."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: content(doc, found, name, problems) for name in REQUIRED_SECTIONS}
    return Goal(doc, title, sections, tuple(problems))


def parse_roadmap(doc: Document) -> Roadmap:
    """Read a roadmap: every list line is an entry, linked or not."""
    problems: list[Problem] = []
    require_title(doc, problems)
    targets: dict[int, str] = {}
    for link in doc.links():
        targets.setdefault(link.index, link.target)
    entries: list[RoadmapEntry] = []
    for index, line in enumerate(doc.lines):
        match = None if line.in_fence else _ENTRY.match(line.text)
        if match:
            checked = match.group(1) is not None and match.group(1) != " "
            entries.append(RoadmapEntry(match.group(2).strip(), targets.get(index), checked, index))
    return Roadmap(doc, tuple(entries), tuple(problems))

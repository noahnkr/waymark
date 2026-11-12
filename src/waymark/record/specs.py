"""Living specs: requirements, each with a SHALL statement and scenarios."""

import re
from dataclasses import dataclass

from waymark.record.outline import (
    collect_sections,
    content,
    parse_facts,
    require_title,
    split_names,
)
from waymark.record.problems import Problem
from waymark.record.text import Document, Section

PURPOSE = "Purpose"
REQUIREMENTS = "Requirements"
REPOS_FACT = "Repos"

_REQUIREMENT = re.compile(r"^Requirement:\s*(\S.*)$")
_SCENARIO = re.compile(r"^Scenario:\s*(\S.*)$")
_STEP = re.compile(r"^\s*[-*]\s+(GIVEN|WHEN|THEN|AND|BUT)\b\s*(.*)$")
_SHALL = re.compile(r"\bSHALL\b")


@dataclass(frozen=True)
class Scenario:
    """A Given/When/Then example of a requirement."""

    name: str
    steps: tuple[tuple[str, str], ...]
    index: int


@dataclass(frozen=True)
class Requirement:
    """One requirement, and where its lines are.

    ``block`` holds its lines from the heading to its last non-blank line.
    ``extent_end`` also takes in the blank lines that follow it.
    """

    name: str
    statement: str
    scenarios: tuple[Scenario, ...]
    start: int
    end: int
    extent_end: int
    block: tuple[str, ...]

    @property
    def key(self) -> str:
        return requirement_key(self.name)


@dataclass(frozen=True)
class Spec:
    """The living description of one area of the system."""

    domain: str
    doc: Document
    title: str
    repos: tuple[str, ...]
    purpose: str
    requirements: tuple[Requirement, ...]
    problems: tuple[Problem, ...]

    def requirement(self, name: str) -> Requirement | None:
        key = requirement_key(name)
        return next((item for item in self.requirements if item.key == key), None)


def requirement_key(name: str) -> str:
    """What a requirement's heading is matched on: its words, ignoring case and spacing."""
    return " ".join(name.split()).casefold()


def named_blocks(
    doc: Document, parent: Section, problems: list[Problem]
) -> list[tuple[str, Section]]:
    """The ``Requirement: <name>`` sections directly under a section."""
    sections = doc.sections(parent.heading.level + 1, parent.body_start, parent.end)
    first = sections[0].start if sections else parent.end
    if doc.text_between(parent.body_start, first):
        problems.append(
            Problem(
                doc.path,
                parent.body_start + 1,
                "unexpected-text",
                f'Text under "{parent.title}" must sit inside a "Requirement: <name>" heading.',
            )
        )
    blocks: list[tuple[str, Section]] = []
    for section in sections:
        match = _REQUIREMENT.match(section.title)
        if match is None:
            problems.append(
                Problem(
                    doc.path,
                    section.start + 1,
                    "requirement-format",
                    f'"{section.title}" is not a requirement heading. '
                    'Write it as "Requirement: <name>".',
                )
            )
        else:
            blocks.append((match.group(1).strip(), section))
    return blocks


def _parse_scenario(
    doc: Document, name: str, section: Section, problems: list[Problem]
) -> Scenario:
    steps: list[tuple[str, str]] = []
    for index in range(section.body_start, section.end):
        line = doc.lines[index]
        if line.is_blank:
            continue
        match = _STEP.match(line.text)
        if match is None:
            problems.append(
                Problem(
                    doc.path,
                    index + 1,
                    "scenario-format",
                    "A scenario is a list of GIVEN, WHEN, THEN and AND lines. "
                    'Write this line as "- WHEN ..." or move it out of the scenario.',
                )
            )
        else:
            steps.append((match.group(1), match.group(2).strip()))
    keywords = {keyword for keyword, _ in steps}
    if not {"WHEN", "THEN"} <= keywords:
        problems.append(
            Problem(
                doc.path,
                section.start + 1,
                "scenario-incomplete",
                f'Scenario "{name}" needs at least a "- WHEN ..." and a "- THEN ..." line.',
            )
        )
    return Scenario(name, tuple(steps), section.start)


def parse_requirement(
    doc: Document, name: str, section: Section, problems: list[Problem]
) -> Requirement:
    """Read one requirement: its statement and its scenarios."""
    level = section.heading.level + 1
    scenario_sections = doc.sections(level, section.body_start, section.end)
    first = scenario_sections[0].start if scenario_sections else section.end
    statement = doc.text_between(section.body_start, first)
    if not _SHALL.search(statement):
        problems.append(
            Problem(
                doc.path,
                section.start + 1,
                "requirement-without-shall",
                f'Requirement "{name}" needs a statement of what the system SHALL do.',
            )
        )
    scenarios: list[Scenario] = []
    for scenario_section in scenario_sections:
        match = _SCENARIO.match(scenario_section.title)
        if match is None:
            problems.append(
                Problem(
                    doc.path,
                    scenario_section.start + 1,
                    "scenario-format",
                    f'"{scenario_section.title}" is not a scenario heading. '
                    'Write it as "Scenario: <name>".',
                )
            )
        else:
            scenarios.append(
                _parse_scenario(doc, match.group(1).strip(), scenario_section, problems)
            )
    if not scenarios:
        problems.append(
            Problem(
                doc.path,
                section.start + 1,
                "requirement-without-scenario",
                f'Requirement "{name}" has no scenario. Add at least one "Scenario: <name>".',
            )
        )
    end = doc.content_end(section.start, section.end)
    block = tuple(line.text for line in doc.lines[section.start : end])
    return Requirement(name, statement, tuple(scenarios), section.start, end, section.end, block)


def parse_requirements(
    doc: Document, parent: Section, problems: list[Problem]
) -> tuple[Requirement, ...]:
    """Read every requirement under a section; a heading used twice is a problem."""
    requirements: list[Requirement] = []
    seen: set[str] = set()
    for name, section in named_blocks(doc, parent, problems):
        requirement = parse_requirement(doc, name, section, problems)
        if requirement.key in seen:
            problems.append(
                Problem(
                    doc.path,
                    section.start + 1,
                    "duplicate-requirement",
                    f'Requirement "{name}" appears twice. A requirement\'s heading is its key; '
                    "rename or merge one of them.",
                )
            )
        seen.add(requirement.key)
        requirements.append(requirement)
    return tuple(requirements)


def parse_spec(domain: str, doc: Document) -> Spec:
    """Read a living spec."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    facts = parse_facts(doc, {REPOS_FACT}, problems, prose=False)
    repos = split_names(facts[REPOS_FACT].value) if REPOS_FACT in facts else ()
    sections = collect_sections(doc, (PURPOSE, REQUIREMENTS), problems, strict=True)
    purpose = content(doc, sections, PURPOSE, problems)
    requirements: tuple[Requirement, ...] = ()
    if REQUIREMENTS in sections:
        requirements = parse_requirements(doc, sections[REQUIREMENTS], problems)
    return Spec(domain, doc, title, repos, purpose, requirements, tuple(problems))

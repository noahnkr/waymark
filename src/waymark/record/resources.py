"""Resources: the as-built facts about one thing outside the repo that a project depends on.

A resource is ``resources/<name>.md``: a title, the lines ``- Kind:``, ``- Serves:``,
``- Status:`` and ``- Verified:``, and six sections that are always present, written
``None.`` when they don't apply. Resources are edited by hand, never through a change's
deltas, and hold no records.
"""

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import Fact, collect_sections, parse_facts, require_title, split_names
from waymark.record.problems import WHOLE_FILE, Problem
from waymark.record.text import Document

KIND = "Kind"
SERVES = "Serves"
STATUS = "Status"
VERIFIED = "Verified"
FACTS = (KIND, SERVES, STATUS, VERIFIED)

WHAT_IT_IS = "What it is"
ACCESS = "Access"
INTERFACE = "Interface"
DATA = "Data"
CONFIGURATION = "Configuration"
VERIFICATION = "Verification"
SECTIONS = (WHAT_IT_IS, ACCESS, INTERFACE, DATA, CONFIGURATION, VERIFICATION)

KINDS = ("service", "platform", "account", "database", "dataset", "document")
ACTIVE = "active"
RETIRED = "retired"
STATUSES = (ACTIVE, RETIRED)
NONE = "none"

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_OUTLINE_LEVELS = (2, 3)


@dataclass(frozen=True)
class Heading:
    """One ``##`` or ``###`` heading of a resource, for the outline the packs carry."""

    level: int
    title: str


@dataclass(frozen=True)
class Resource:
    """A resource. A value that is missing or not in its form is None, and reported."""

    name: str
    doc: Document
    title: str
    kind: str | None
    serves: tuple[str, ...]
    serves_line: int | None
    """The 1-based line of ``- Serves:``, for messages about the specs it names."""
    status: str | None
    verified: datetime.date | None
    sections: Mapping[str, str]
    outline: tuple[Heading, ...]
    problems: tuple[Problem, ...]

    @property
    def active(self) -> bool:
        return self.status == ACTIVE


def _listed(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _line(fact: Fact) -> int:
    return fact.index + 1


def parse_resource(name: str, doc: Document) -> Resource:
    """Read a resource, reporting each line or section that is missing or not in its form."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    every_fact = parse_facts(doc, set(FACTS), problems, prose=True)
    facts = {key: fact for key, fact in every_fact.items() if fact.bullet}
    for key in FACTS:
        if key not in facts:
            problems.append(
                Problem(
                    doc.path,
                    WHOLE_FILE,
                    "missing-line",
                    f'A resource has a "- {key}:" line under its title. Add it.',
                )
            )

    kind: str | None = None
    if KIND in facts:
        value = facts[KIND].value
        if value in KINDS:
            kind = value
        else:
            problems.append(
                Problem(
                    doc.path,
                    _line(facts[KIND]),
                    "unknown-kind",
                    f'"{value}" is not a kind of resource. The kinds are {_listed(KINDS)}.',
                )
            )

    status: str | None = None
    if STATUS in facts:
        value = facts[STATUS].value
        if value in STATUSES:
            status = value
        else:
            problems.append(
                Problem(
                    doc.path,
                    _line(facts[STATUS]),
                    "unknown-status",
                    f'"{value}" is not a status. A resource is `{ACTIVE}` or `{RETIRED}`.',
                )
            )

    verified: datetime.date | None = None
    if VERIFIED in facts:
        value = facts[VERIFIED].value
        try:
            verified = datetime.date.fromisoformat(value) if _DATE.match(value) else None
        except ValueError:
            verified = None
        if verified is None:
            problems.append(
                Problem(
                    doc.path,
                    _line(facts[VERIFIED]),
                    "invalid-date",
                    f'"{value}" is not a date. The date is written YYYY-MM-DD, such as '
                    f'"- {VERIFIED}: 2026-11-17".',
                )
            )

    serves: tuple[str, ...] = ()
    serves_line: int | None = None
    if SERVES in facts:
        value = facts[SERVES].value
        serves = () if value.strip().casefold() == NONE else split_names(value)
        serves_line = _line(facts[SERVES])

    found = collect_sections(doc, SECTIONS, problems)
    sections = {
        section: doc.body(found[section]) if section in found else "" for section in SECTIONS
    }
    outline = tuple(
        Heading(heading.level, heading.title)
        for heading in doc.headings
        if heading.level in _OUTLINE_LEVELS
    )
    return Resource(
        name,
        doc,
        title,
        kind,
        serves,
        serves_line,
        status,
        verified,
        sections,
        outline,
        tuple(problems),
    )


def unknown_specs(resource: Resource, specs: Mapping[str, object]) -> list[Problem]:
    """A problem for each spec the ``- Serves:`` line names that isn't in the record."""
    unknown = [name for name in resource.serves if name not in specs]
    if not unknown:
        return []
    known = ", ".join(sorted(specs)) or "none"
    return [
        Problem(
            resource.doc.path,
            resource.serves_line or WHOLE_FILE,
            "unknown-spec",
            f'The resource serves "{name}", which is not a spec (specs: {known}). Fix the name, '
            f'or write "- {SERVES}: {NONE}".',
        )
        for name in unknown
    ]

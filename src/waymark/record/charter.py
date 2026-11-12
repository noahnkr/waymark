"""The charter: what the project is, the context every agent gets, and rules per step."""

from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.outline import collect_sections, require_title
from waymark.record.problems import Problem
from waymark.record.terms import Step
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


@dataclass(frozen=True)
class Charter:
    """The project's charter.

    ``context`` goes to every agent. ``rules`` holds the text for each workflow
    step that has any; an agent gets only its own step's rules.
    """

    doc: Document
    title: str
    sections: Mapping[str, str]
    context: str
    rules: Mapping[Step, str]
    problems: tuple[Problem, ...]


def parse_charter(doc: Document) -> Charter:
    """Read the charter. Sections may be empty while the charter is still a skeleton."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    found = collect_sections(doc, REQUIRED_SECTIONS, problems)
    sections = {name: doc.body(found[name]) if name in found else "" for name in REQUIRED_SECTIONS}

    rules: dict[Step, str] = {}
    if RULES in found:
        parent = found[RULES]
        for section in doc.sections(3, parent.body_start, parent.end):
            name = section.title.casefold()
            if name not in set(Step):
                steps = ", ".join(step.value for step in Step)
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "unknown-step",
                        f'"{section.title}" is not a workflow step, so no agent would get '
                        f"these rules. Use one of: {steps}.",
                    )
                )
            elif Step(name) in rules:
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "duplicate-section",
                        f'The rules for "{name}" appear twice. Merge the two sections.',
                    )
                )
            else:
                text = doc.body(section)
                if text:
                    rules[Step(name)] = text
    return Charter(doc, title, sections, sections[CONTEXT], rules, tuple(problems))

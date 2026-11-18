"""The edits wm makes to record files: the lines it owns, and nothing else.

Every function takes a parsed artifact and returns the file's new text. Lines
that aren't touched come back byte for byte, with their line endings.
"""

import re
from collections.abc import Sequence

from waymark.record.artifacts.proposal import OUTCOME, Proposal
from waymark.record.artifacts.tasks import LOG_SECTION, Tasks
from waymark.record.markdown.text import Document, Section

_BOX = re.compile(r"^- \[[ xX]\]")


def _lines(doc: Document) -> list[str]:
    """The file's lines, each ending in a line break."""
    lines = doc.raw_lines()
    if lines and not doc.lines[-1].ending:
        lines[-1] += doc.newline
    return lines


def edit_item(
    tasks: Tasks,
    number: str,
    *,
    ticked: bool | None = None,
    add: Sequence[str] = (),
) -> str:
    """Change one item's evidence: its tick, and records added at its end.

    Records are never removed; a later record supersedes an earlier one.
    """
    item = tasks.item(number)
    assert item is not None
    newline = tasks.doc.newline
    lines = _lines(tasks.doc)
    lines[item.end : item.end] = [f"  - {text}{newline}" for text in add]
    if ticked is not None:
        mark = "x" if ticked else " "
        lines[item.index] = _BOX.sub(f"- [{mark}]", lines[item.index], count=1)
    return "".join(lines)


def append_log(tasks: Tasks, record: str, findings: Sequence[str] = ()) -> str:
    """Append a record, and the findings under it, to the change's Log section.

    The section is created at the end of the task list when it isn't there yet.
    """
    return _append_to_section(tasks, tasks.log_section, LOG_SECTION, record, findings)


def _append_to_section(
    tasks: Tasks, section: Section | None, title: str, record: str, findings: Sequence[str]
) -> str:
    newline = tasks.doc.newline
    lines = _lines(tasks.doc)
    added = [f"- {record}{newline}", *(f"  - {finding}{newline}" for finding in findings)]
    if section is None:
        while lines and not lines[-1].strip():
            lines.pop()
        return "".join([*lines, newline, f"## {title}{newline}", newline, *added])
    end = section.end
    while end > section.body_start and not lines[end - 1].strip():
        end -= 1
    if end == section.body_start:
        added = [newline, *added]
    lines[end:end] = added
    return "".join(lines)


def set_outcome(proposal: Proposal, outcome: str) -> str:
    """Write the outcome section, replacing one that is already there."""
    doc = proposal.doc
    newline = doc.newline
    lines = _lines(doc)
    body = [f"## {OUTCOME}{newline}", newline, *(text + newline for text in outcome.split("\n"))]
    section = next((s for s in doc.sections(2) if s.title.casefold() == OUTCOME.casefold()), None)
    if section is None:
        while lines and not lines[-1].strip():
            lines.pop()
        return "".join([*lines, newline, *body])
    trailing = [newline] if section.end < len(lines) else []
    lines[section.start : section.end] = [*body, *trailing]
    return "".join(lines)


def replace_spans(doc: Document, replacements: dict[tuple[int, int, int], str]) -> str:
    """Replace spans of text inside lines; keys are (line index, start, end)."""
    lines = doc.raw_lines()
    offset = 1 if doc.bom else 0
    for (index, start, end), text in sorted(replacements.items(), reverse=True):
        shift = offset if index == 0 else 0
        line = lines[index]
        lines[index] = line[: start + shift] + text + line[end + shift :]
    return "".join(lines)

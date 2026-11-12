"""The edits wm makes to record files: the lines it owns, and nothing else.

Every function takes a parsed artifact and returns the file's new text. Lines
that aren't touched come back byte for byte, with their line endings.
"""

import re
from collections.abc import Sequence

from waymark.record.outline import parse_facts
from waymark.record.proposal import ACCEPTED, OUTCOME, OWNER, PATH, SYNCED, Proposal
from waymark.record.tasks import Tasks
from waymark.record.text import Document

_BOX = re.compile(r"^- \[[ xX]\]")
_FORMAT_LINE = re.compile(r"^record_format\s*=\s*\d+", re.MULTILINE)


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
    remove: Sequence[str] = (),
    add: Sequence[str] = (),
) -> str:
    """Change one item's evidence: its tick, its labeled lines, and new lines at its end."""
    item = tasks.item(number)
    assert item is not None
    newline = tasks.doc.newline
    lines = _lines(tasks.doc)
    lines[item.end : item.end] = [f"  - {text}{newline}" for text in add]
    spans = sorted((item.spans[label] for label in remove if label in item.spans), reverse=True)
    for start, end in spans:
        del lines[start:end]
    if ticked is not None:
        mark = "x" if ticked else " "
        lines[item.index] = _BOX.sub(f"- [{mark}]", lines[item.index], count=1)
    return "".join(lines)


def set_fact(proposal: Proposal, key: str, line: str | None) -> str:
    """Write, replace or remove one of wm's fact lines under a proposal's title."""
    doc = proposal.doc
    newline = doc.newline
    lines = _lines(doc)
    facts = parse_facts(doc, {OWNER, PATH, ACCEPTED, SYNCED}, [], prose=True)
    if key in facts:
        index = facts[key].index
        lines[index : index + 1] = [] if line is None else [line + newline]
    elif line is not None:
        last = max(fact.index for fact in facts.values())
        lines[last + 1 : last + 1] = [line + newline]
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


def set_record_format(config_text: str, number: int) -> str:
    """Advance the record format number in the settings, leaving every other line alone."""
    assert _FORMAT_LINE.search(config_text) is not None
    return _FORMAT_LINE.sub(f"record_format = {number}", config_text, count=1)


def replace_spans(doc: Document, replacements: dict[tuple[int, int, int], str]) -> str:
    """Replace spans of text inside lines; keys are (line index, start, end)."""
    lines = doc.raw_lines()
    offset = 1 if doc.bom else 0
    for (index, start, end), text in sorted(replacements.items(), reverse=True):
        shift = offset if index == 0 else 0
        line = lines[index]
        lines[index] = line[: start + shift] + text + line[end + shift :]
    return "".join(lines)

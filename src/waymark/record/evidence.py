"""Gate evidence in a record file: the lines only wm writes.

Used to tell whether an edit adds, changes or removes evidence. The evidence
is every tick in a task list, every record wm writes under an item or in the
Log, and every finding under a review in the Log.
"""

import re
from collections import Counter

from waymark.record import records
from waymark.record.changes import TASKS_FILE
from waymark.record.tasks import LOG_SECTION
from waymark.record.text import Document

_ITEM = re.compile(r"^- \[([ xX])\] (\d+\.\d+)\s")
_HEADING = re.compile(r"^## (.*)$")
_LIST_LINE = re.compile(r"^\s*[-*] (.*)$")
_NOTE = re.compile(r"^  [-*] Note: \S")


def evidence(relative: str, text: str) -> Counter[str]:
    """Every piece of evidence in a task list, each named so it can be reported."""
    found: Counter[str] = Counter()
    if relative.rsplit("/", 1)[-1] != TASKS_FILE:
        return found
    number = "?"
    in_log = False
    for line in Document.parse(relative, text).lines:
        if line.in_fence:
            continue
        heading = _HEADING.match(line.text)
        if heading:
            in_log = heading.group(1).strip().casefold() == LOG_SECTION.casefold()
            continue
        if in_log:
            if not line.is_blank:
                found[f'"{line.text.strip()}" in the {LOG_SECTION} section'] += 1
            continue
        item = _ITEM.match(line.text)
        if item:
            number = item.group(2)
            if item.group(1) != " ":
                found[f"the tick on item {number}"] += 1
            continue
        listed = _LIST_LINE.match(line.text)
        if listed and records.looks_like_record(listed.group(1)):
            found[f'"{listed.group(1).strip()}" under item {number}'] += 1
    return found


def evidence_changes(relative: str, before: str, after: str) -> list[str]:
    """The evidence an edit would add or take away; empty when it leaves evidence alone."""
    old, new = evidence(relative, before), evidence(relative, after)
    added = [f"adds {name}" for name in sorted((new - old).elements())]
    removed = [f"removes {name}" for name in sorted((old - new).elements())]
    return added + removed


def only_adds_notes(before: str, after: str) -> bool:
    """Whether an edit to a task list does nothing but add note lines."""
    old = Counter(Document.parse("", before).raw_lines())
    new = Counter(Document.parse("", after).raw_lines())
    if old - new:
        return False
    return all(_NOTE.match(line) or line.startswith("    ") for line in (new - old).elements())

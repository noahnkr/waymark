"""Gate evidence in a record file: the lines only wm writes.

Used to tell whether an edit adds, changes or removes evidence. The evidence
is the ticks, blockers, spec gaps and review records in a task list, and the
acceptance, synced and override lines in a proposal.
"""

import re
from collections import Counter

from waymark.record.changes import PROPOSAL_FILE, TASKS_FILE
from waymark.record.tasks import is_evidence_line
from waymark.record.text import Document

_ITEM = re.compile(r"^- \[([ xX])\] (\d+\.\d+)\s")
_PROPOSAL_EVIDENCE = re.compile(r"^(Accepted|Synced|Review override):")
_NOTE = re.compile(r"^  [-*] Note: \S")


def evidence(relative: str, text: str) -> Counter[str]:
    """Every piece of evidence in a record file, each named so it can be reported."""
    name = relative.rsplit("/", 1)[-1]
    found: Counter[str] = Counter()
    doc = Document.parse(relative, text)
    if name == TASKS_FILE:
        number = "?"
        for line in doc.lines:
            if line.in_fence:
                continue
            item = _ITEM.match(line.text)
            if item:
                number = item.group(2)
                if item.group(1) != " ":
                    found[f"the tick on item {number}"] += 1
            elif is_evidence_line(line.text):
                found[f'"{line.text.strip()[2:]}" under item {number}'] += 1
    elif name == PROPOSAL_FILE:
        for line in doc.lines:
            if not line.in_fence and _PROPOSAL_EVIDENCE.match(line.text):
                found[f'the "{line.text.strip()}" line'] += 1
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

"""Roadmaps: add, drop and move a milestone's roadmap lines, and log each change of plan.

The roadmap and its Log are changed only through these commands, ``wm new change
--milestone`` and ``wm archive``. Each command edits the roadmap's lines as text, keeping
the file's line endings, and appends its record to the milestone's Log in the same write.
"""

import datetime
from dataclasses import dataclass
from pathlib import Path

from waymark.record.artifacts.milestones import ROADMAP, Milestone, Roadmap, append_milestone_log
from waymark.record.evidence import records
from waymark.record.evidence.records import RecordError, RecordKind
from waymark.record.markdown import labels
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.text import BOM, Document
from waymark.record.names import NAME_RULE, is_valid_name
from waymark.record.record import Record
from waymark.record.state import entry_change
from waymark.record.writing.store import Transaction
from waymark.services.common import Done, Refusal, commit, one_line, open_record


@dataclass
class _Lines:
    """A file's lines and their endings, to edit and join again."""

    doc: Document
    texts: list[str]
    endings: list[str]

    @classmethod
    def of(cls, doc: Document) -> "_Lines":
        return cls(doc, [line.text for line in doc.lines], [line.ending for line in doc.lines])

    def text(self) -> str:
        body = "".join(t + e for t, e in zip(self.texts, self.endings, strict=True))
        return (BOM if self.doc.bom else "") + body

    def insert(self, at: int, text: str) -> None:
        if at > 0 and not self.endings[at - 1]:
            self.endings[at - 1] = self.doc.newline
        self.texts.insert(at, text)
        self.endings.insert(at, self.doc.newline)

    def pop(self, at: int) -> str:
        self.endings.pop(at)
        return self.texts.pop(at)


def _milestone(record: Record, name: str) -> tuple[Milestone, Roadmap]:
    milestone = record.milestones.get(name)
    if milestone is None or milestone.roadmap is None:
        known = ", ".join(sorted(record.milestones)) or "none"
        raise Refusal(f'"{name}" is not an active milestone (the active ones: {known}).')
    return milestone, milestone.roadmap


def _line_of(roadmap: Roadmap, change: str) -> int | None:
    """The index of the roadmap line for a change, or None when it has none."""
    for entry in roadmap.entries:
        if entry_change(roadmap.doc.path, entry) == change:
            return entry.index
    return None


def _require_line(roadmap: Roadmap, milestone: str, change: str) -> int:
    index = _line_of(roadmap, change)
    if index is None:
        raise Refusal(
            f'"{change}" is not on the roadmap of "{milestone}". Add it with '
            f'"wm roadmap add {milestone} {change} "<description>"".'
        )
    return index


def _who(record: Record, by: str | None) -> str | None:
    try:
        return records.who_for(record.project.root, by)
    except RecordError as error:
        raise Refusal(str(error)) from error


def _write(record: Record, lines: _Lines, entry: records.Record) -> tuple[str, ...]:
    """Write the edited roadmap with the record appended to the milestone's Log."""
    try:
        line = records.render(entry)
    except RecordError as error:
        raise Refusal(str(error)) from error
    edited = Document.parse(lines.doc.path, lines.text())
    transaction = Transaction(record.files)
    transaction.write(lines.doc.path, append_milestone_log(edited, line))
    return commit(transaction)


def add(
    start: Path,
    milestone: str,
    change: str,
    description: str,
    today: datetime.date,
    *,
    by: str | None = None,
) -> Done:
    """Add a planned line for a change at the end of a milestone's roadmap."""
    record = open_record(start, writing=True)
    _, roadmap = _milestone(record, milestone)
    if not is_valid_name(change):
        raise Refusal(f'"{change}" is not a valid change name: {NAME_RULE}.')
    text = one_line(description, "a description of the change")
    if _line_of(roadmap, change) is not None:
        raise Refusal(f'"{change}" is already on the roadmap of "{milestone}".')
    lines = _Lines.of(roadmap.doc)
    if roadmap.entries:
        at = roadmap.entries[-1].index + 1
    else:
        section = next(
            (s for s in roadmap.doc.sections(2) if s.title.casefold() == ROADMAP.casefold()), None
        )
        if section is None:
            raise Refusal(
                f'The milestone "{milestone}" has no "## {ROADMAP}" section. Add the heading '
                "after its Non-goals, then add the line."
            )
        filled = [i for i in range(section.start + 1, section.end) if lines.texts[i].strip()]
        at = filled[-1] + 1 if filled else section.start + 1
        if not filled:
            lines.insert(at, "")
            at += 1
    lines.insert(at, f"- {change}: {text}")
    entry = records.Record(RecordKind.ADDED, today, who=_who(record, by), text=text, change=change)
    paths = _write(record, lines, entry)
    return Done(f'Added "{change}" to the roadmap of "{milestone}".', paths)


def drop(
    start: Path,
    milestone: str,
    change: str,
    reason: str,
    today: datetime.date,
    *,
    by: str | None = None,
) -> Done:
    """Take a change's line off a milestone's roadmap, with the reason in the Log."""
    record = open_record(start, writing=True)
    _, roadmap = _milestone(record, milestone)
    text = one_line(reason, "the reason for dropping it")
    index = _require_line(roadmap, milestone, change)
    member = record.changes.get(change)
    if member is not None and member.proposal and member.proposal.milestone == milestone:
        raise Refusal(
            f'"{change}" is an active change whose proposal names "{milestone}" in its '
            f'"{label_line(labels.MILESTONE)}" line. Take that line off its proposal first, '
            "which withdraws its "
            "acceptance, or archive or delete the change, then drop it."
        )
    lines = _Lines.of(roadmap.doc)
    lines.pop(index)
    entry = records.Record(
        RecordKind.DROPPED, today, who=_who(record, by), text=text, change=change
    )
    paths = _write(record, lines, entry)
    return Done(f'Dropped "{change}" from the roadmap of "{milestone}".', paths)


def move(
    start: Path,
    milestone: str,
    change: str,
    today: datetime.date,
    *,
    after: str | None = None,
    by: str | None = None,
) -> Done:
    """Move a change's line after another change's line, or to the top with no ``after``."""
    record = open_record(start, writing=True)
    _, roadmap = _milestone(record, milestone)
    index = _require_line(roadmap, milestone, change)
    if after == change:
        raise Refusal(f'"{change}" can\'t be moved after itself.')
    target = _require_line(roadmap, milestone, after) if after is not None else None
    lines = _Lines.of(roadmap.doc)
    moved = lines.pop(index)
    # The line is out, so a target below it has moved up by one.
    after_target = target + 1 if target is not None and target < index else target
    lines.insert(roadmap.entries[0].index if after_target is None else after_target, moved)
    entry = records.Record(
        RecordKind.MOVED, today, who=_who(record, by), change=change, after=after
    )
    paths = _write(record, lines, entry)
    where = f'after "{after}"' if after else "to the top"
    return Done(f'Moved "{change}" {where} on the roadmap of "{milestone}".', paths)

"""Task lists: numbered sections of checkbox items, with the evidence under each item.

An item's definition is its number, title, review level, criteria, verification
and repo. Its evidence is its tick, its blocker, its spec gap and its review
records.
"""

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from waymark.record.problems import Problem
from waymark.record.terms import ReviewLevel, Verdict
from waymark.record.text import Document, Section

BLOCKED = "Blocked"
SPEC_GAP = "Spec gap"

_SECTION = re.compile(r"^(\d+)\.\s+(\S.*)$")
_ITEM = re.compile(r"^- \[([ xX])\] (\d+)\.(\d+)\s+(\S.*?)\s*$")
_LEVEL_TAG = re.compile(r"\s+`review:\s*([A-Za-z-]+)`$")
_LIST_LINE = re.compile(r"^(?:[-*+]|\d+[.)])(?:\s|$)")
_FIELD = re.compile(r"^  [-*] (\S.*)$")
_LABELED = re.compile(r"^(Criteria|Verify|Repo|Blocked|Spec gap|Note):(?:\s+(.*))?$")
_EVIDENCE = re.compile(r"^\((review|self-review|reopened|resolved)\)")
_REVIEW = re.compile(r"^\(review\) (\d{4}-\d{2}-\d{2}) (pass|changes|spec-gap): (\S.*)$")
_SELF_REVIEW = re.compile(r"^\(self-review\) (\d{4}-\d{2}-\d{2}): (\S.*)$")
_REOPENED = re.compile(r"^\(reopened\) (\d{4}-\d{2}-\d{2})$")
_RESOLVED = re.compile(r"^\(resolved\) (\d{4}-\d{2}-\d{2}): (\S.*)$")

_FORMATS = (
    '"(review) YYYY-MM-DD pass|changes|spec-gap: <reasons>", '
    '"(self-review) YYYY-MM-DD: <summary>", "(reopened) YYYY-MM-DD" or '
    '"(resolved) YYYY-MM-DD: <what was decided>"'
)


class RecordKind(StrEnum):
    """The kinds of review record under an item."""

    REVIEW = "review"
    SELF_REVIEW = "self-review"
    REOPENED = "reopened"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class ReviewRecord:
    """One record: a reviewer's verdict, a self-review, a reopening or a resolution."""

    kind: RecordKind
    date: datetime.date
    verdict: Verdict | None
    text: str
    index: int


@dataclass(frozen=True)
class Item:
    """One task item, with what is written under it.

    ``end`` is the index after the item's last line. ``spans`` gives the line
    range of each labeled line under the item.
    """

    number: str
    section: int
    title: str
    ticked: bool
    level_tag: ReviewLevel | None
    criteria: str | None
    verify: str | None
    repo: str | None
    blocked: str | None
    spec_gap: str | None
    notes: tuple[str, ...]
    records: tuple[ReviewRecord, ...]
    index: int
    end: int
    spans: Mapping[str, tuple[int, int]]

    def level(self, default: ReviewLevel) -> ReviewLevel:
        """The item's review level: its tag, or the project default."""
        return self.level_tag or default


@dataclass(frozen=True)
class TaskSection:
    """A numbered section of a task list."""

    number: int
    title: str
    index: int


@dataclass(frozen=True)
class Tasks:
    """A change's task list."""

    doc: Document
    sections: tuple[TaskSection, ...]
    items: tuple[Item, ...]
    problems: tuple[Problem, ...]

    def item(self, number: str) -> Item | None:
        return next((item for item in self.items if item.number == number), None)


@dataclass
class _Draft:
    """An item while its lines are still being read."""

    number: str
    section: int
    title: str
    ticked: bool
    level_tag: ReviewLevel | None
    index: int
    end: int
    fields: dict[str, list[str]] = field(default_factory=dict)
    spans: dict[str, tuple[int, int]] = field(default_factory=dict)
    notes: list[list[str]] = field(default_factory=list)
    records: list[ReviewRecord] = field(default_factory=list)
    open_text: list[str] | None = None
    open_label: str | None = None

    def extend(self, index: int, text: str) -> None:
        """Add a continuation line to the field that is still open."""
        assert self.open_text is not None
        self.open_text.append(text)
        self.end = index + 1
        if self.open_label is not None:
            self.spans[self.open_label] = (self.spans[self.open_label][0], index + 1)

    def finish(self) -> Item:
        def single(label: str) -> str | None:
            return "\n".join(self.fields[label]).strip() if label in self.fields else None

        return Item(
            number=self.number,
            section=self.section,
            title=self.title,
            ticked=self.ticked,
            level_tag=self.level_tag,
            criteria=single("Criteria"),
            verify=single("Verify"),
            repo=single("Repo"),
            blocked=single(BLOCKED),
            spec_gap=single(SPEC_GAP),
            notes=tuple("\n".join(note).strip() for note in self.notes),
            records=tuple(self.records),
            index=self.index,
            end=self.end,
            spans=dict(self.spans),
        )


class _Parser:
    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.problems: list[Problem] = []
        self.sections: list[TaskSection] = []
        self.items: list[Item] = []
        self.draft: _Draft | None = None

    def problem(self, index: int, code: str, message: str) -> None:
        self.problems.append(Problem(self.doc.path, index + 1, code, message))

    def close_item(self) -> None:
        if self.draft is not None:
            self.items.append(self.draft.finish())
            self.draft = None

    def date(self, index: int, text: str) -> datetime.date | None:
        try:
            return datetime.date.fromisoformat(text)
        except ValueError:
            self.problem(
                index, "malformed-evidence", f'"{text}" is not a date. Write it as YYYY-MM-DD.'
            )
            return None

    def evidence(self, index: int, text: str) -> None:
        draft = self.draft
        assert draft is not None
        review = _REVIEW.match(text)
        self_review = _SELF_REVIEW.match(text)
        resolved = _RESOLVED.match(text)
        match = review or self_review or resolved or _REOPENED.match(text)
        if match is None:
            self.problem(
                index,
                "malformed-evidence",
                f"This review record doesn't follow the format. Write it as {_FORMATS}.",
            )
            return
        date = self.date(index, match.group(1))
        if date is None:
            return
        if review:
            record = ReviewRecord(
                RecordKind.REVIEW, date, Verdict(review.group(2)), review.group(3).strip(), index
            )
        elif self_review:
            record = ReviewRecord(
                RecordKind.SELF_REVIEW, date, None, self_review.group(2).strip(), index
            )
        elif resolved:
            record = ReviewRecord(RecordKind.RESOLVED, date, None, resolved.group(2).strip(), index)
        else:
            record = ReviewRecord(RecordKind.REOPENED, date, None, "", index)
        draft.records.append(record)

    def labeled(self, index: int, label: str, value: str) -> None:
        draft = self.draft
        assert draft is not None
        if label == "Note":
            draft.notes.append([value])
            draft.open_text = draft.notes[-1]
        elif label in draft.fields:
            self.problem(
                index, "duplicate-field", f'"{label}:" appears twice under this item. Keep one.'
            )
        else:
            draft.fields[label] = [value]
            draft.spans[label] = (index, index + 1)
            draft.open_text = draft.fields[label]
            draft.open_label = label

    def field_line(self, index: int, text: str) -> None:
        draft = self.draft
        assert draft is not None
        draft.open_text = None
        draft.open_label = None
        draft.end = index + 1
        labeled = _LABELED.match(text)
        if labeled:
            self.labeled(index, labeled.group(1), (labeled.group(2) or "").strip())
        elif _EVIDENCE.match(text):
            self.evidence(index, text)
        else:
            self.problem(
                index,
                "unrecognized-item-line",
                'A line under an item starts with "Criteria:", "Verify:", "Repo:", "Blocked:", '
                '"Spec gap:" or "Note:", or is a review record. Label this line, or make it '
                'a "Note:".',
            )

    def item_line(self, index: int, section: TaskSection | None, text: str) -> bool:
        match = _ITEM.match(text)
        if match is None:
            return False
        self.close_item()
        title = match.group(4)
        level_tag: ReviewLevel | None = None
        tag = _LEVEL_TAG.search(title)
        if tag:
            title = title[: tag.start()].rstrip()
            if tag.group(1) in set(ReviewLevel):
                level_tag = ReviewLevel(tag.group(1))
            else:
                levels = ", ".join(level.value for level in ReviewLevel)
                self.problem(
                    index,
                    "unknown-review-level",
                    f'"{tag.group(1)}" is not a review level. Use one of: {levels}.',
                )
        number = f"{match.group(2)}.{match.group(3)}"
        if section is None:
            self.problem(
                index,
                "item-outside-section",
                f'Item {number} is not under a numbered section. Put it under "## <n>. <title>".',
            )
        elif int(match.group(2)) != section.number:
            self.problem(
                index,
                "item-number",
                f"Item {number} sits in section {section.number}. "
                f"Number it {section.number}.<n>, or move it to its own section.",
            )
        self.draft = _Draft(
            number=number,
            section=int(match.group(2)),
            title=title,
            ticked=match.group(1) != " ",
            level_tag=level_tag,
            index=index,
            end=index + 1,
        )
        return True

    def body_line(self, index: int, section: TaskSection | None) -> None:
        line = self.doc.lines[index]
        text = line.text
        draft = self.draft
        if line.in_fence or line.is_blank:
            if draft is not None and draft.open_text is not None and line.in_fence:
                draft.extend(index, text.strip())
            return
        if not text.startswith(" "):
            if self.item_line(index, section, text):
                return
            self.close_item()
            if _LIST_LINE.match(text):
                self.problem(
                    index,
                    "malformed-item",
                    'An item is written "- [ ] <section>.<n> <title>", for example '
                    '"- [ ] 1.1 Add the endpoint". Fix this line, or indent it under an item.',
                )
            return
        if draft is None:
            return
        field_match = _FIELD.match(text)
        if field_match:
            self.field_line(index, field_match.group(1).strip())
        elif draft.open_text is not None:
            draft.extend(index, text.strip())
        else:
            self.problem(
                index,
                "unrecognized-item-line",
                'Lines under an item are a list indented by two spaces, such as "  - Criteria: '
                '...". Fix the indentation, or label the line.',
            )

    def section(self, section: Section) -> TaskSection | None:
        match = _SECTION.match(section.title)
        if match is None:
            self.problem(
                section.start,
                "task-section-format",
                f'"{section.title}" is not a task section. Write it as "## <n>. <title>".',
            )
            return None
        task_section = TaskSection(int(match.group(1)), match.group(2).strip(), section.start)
        self.sections.append(task_section)
        return task_section

    def check_numbering(self) -> None:
        last_section = 0
        for task_section in self.sections:
            if task_section.number <= last_section:
                self.problem(
                    task_section.index,
                    "section-number",
                    f"Section {task_section.number} is out of order or used twice. "
                    "Section numbers go up and are never reused.",
                )
            last_section = max(last_section, task_section.number)
        last_item: dict[int, int] = {}
        for item in self.items:
            position = int(item.number.split(".")[1])
            if position <= last_item.get(item.section, 0):
                self.problem(
                    item.index,
                    "item-number",
                    f"Item {item.number} is out of order or used twice. Item numbers go up "
                    "within a section and are never reused; append new items at the end.",
                )
            last_item[item.section] = max(last_item.get(item.section, 0), position)

    def check_fields(self) -> None:
        for item in self.items:
            values = {
                "Criteria": item.criteria,
                "Verify": item.verify,
                "Repo": item.repo,
                BLOCKED: item.blocked,
                SPEC_GAP: item.spec_gap,
            }
            for label, value in values.items():
                if value is not None and not value:
                    self.problem(
                        item.index,
                        "empty-field",
                        f'"{label}:" under item {item.number} is empty. '
                        "Write it, or remove the line.",
                    )

    def parse(self) -> Tasks:
        doc = self.doc
        sections = doc.sections(2)
        first = sections[0].start if sections else len(doc.lines)
        for index in range(first):
            self.body_line(index, None)
        self.close_item()
        for section in sections:
            task_section = self.section(section)
            for index in range(section.body_start, section.end):
                self.body_line(index, task_section)
            self.close_item()
        self.check_numbering()
        self.check_fields()
        return Tasks(doc, tuple(self.sections), tuple(self.items), tuple(self.problems))


def parse_tasks(doc: Document) -> Tasks:
    """Read a task list."""
    return _Parser(doc).parse()


def is_evidence_line(text: str) -> bool:
    """Whether a line under an item is gate evidence: a blocker, a spec gap or a record."""
    match = _FIELD.match(text)
    if match is None:
        return False
    content = match.group(1)
    return (
        content.startswith((f"{BLOCKED}:", f"{SPEC_GAP}:")) or _EVIDENCE.match(content) is not None
    )

"""Task lists: numbered sections of checkbox items, then the change's Log.

An item's definition is its number, title, build tag, criteria, verification and
repo. Its evidence is its tick and the records under it: blockers, spec gaps,
notes, reopenings and resolutions. The records about the whole change, with the
findings under its reviews, sit in a ``## Log`` section at the end.

A task list is read in the record's format. Format 1 kept ``Blocked:``,
``Spec gap:`` and ``Note:`` lines under items and a ``## Review`` section, and
its archived changes may still carry an item ``review:`` tag and review records
under items; they are read so the archive shows as it was written.
"""

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from waymark.record import records
from waymark.record.problems import Problem
from waymark.record.records import RecordKind
from waymark.record.terms import ReviewLevel, ReviewSeverity, Verdict
from waymark.record.text import Document, Section

BLOCKED = "Blocked"
SPEC_GAP = "Spec gap"

_SECTION = re.compile(r"^(\d+)\.\s+(\S.*)$")
_ITEM = re.compile(r"^- \[([ xX])\] (\d+)\.(\d+)\s+(\S.*?)\s*$")
_TAG = re.compile(r"\s+`(review|build):\s*([A-Za-z-]+)`$")
DELEGATE = "delegate"
_LIST_LINE = re.compile(r"^(?:[-*+]|\d+[.)])(?:\s|$)")
_FIELD = re.compile(r"^  [-*] (\S.*)$")
_LABELED = re.compile(r"^(Criteria|Verify|Repo|Blocked|Spec gap|Note):(?:\s+(.*))?$")
_EVIDENCE = re.compile(r"^\((review|self-review|reopened|resolved)\)")
_REVIEW = re.compile(r"^\(review\) (\d{4}-\d{2}-\d{2}) (pass|changes|spec-gap): (\S.*)$")
_SELF_REVIEW = re.compile(r"^\(self-review\) (\d{4}-\d{2}-\d{2}): (\S.*)$")
_REOPENED = re.compile(r"^\(reopened\) (\d{4}-\d{2}-\d{2})$")
_RESOLVED = re.compile(r"^\(resolved\) (\d{4}-\d{2}-\d{2}): (\S.*)$")
_CHANGE_REVIEW = re.compile(
    r"^\(review\) (\d{4}-\d{2}-\d{2}) (pass|changes|spec-gap)((?: \d+\.\d+)*): (\S.*)$"
)
_RECORD_LINE = re.compile(r"^[-*] (\(.*)$")
_FINDING = re.compile(r"^(critical|warning|suggestion): (\S.*?): (\S.*)$")
REVIEW_SECTION = "Review"

_CHANGE_FORMATS = (
    '"- (review) YYYY-MM-DD pass|spec-gap: <reasons>", '
    '"- (review) YYYY-MM-DD changes <item> <item>...: <reasons>", '
    '"- (self-review) YYYY-MM-DD: <summary>" or "- (resolved) YYYY-MM-DD: <what was decided>"'
)
_FINDING_FORMAT = '"  - critical|warning|suggestion: <place>: <text>"'

_FORMATS = (
    '"(review) YYYY-MM-DD pass|changes|spec-gap: <reasons>", '
    '"(self-review) YYYY-MM-DD: <summary>", "(reopened) YYYY-MM-DD" or '
    '"(resolved) YYYY-MM-DD: <what was decided>"'
)


LOG_SECTION = "Log"
LATEST_FORMAT = 2
"""The record format whose task lists hold records and a Log section."""

_REVIEW_KINDS = (RecordKind.REVIEW, RecordKind.SELF_REVIEW, RecordKind.RESOLVED)
_OLD_LABELS = (BLOCKED, SPEC_GAP, "Note")


@dataclass(frozen=True)
class Finding:
    """One finding of a review: how much it matters, where, and what."""

    severity: ReviewSeverity
    place: str
    text: str
    index: int


@dataclass(frozen=True)
class ReviewRecord:
    """One record: a reviewer's verdict, a self-review, a reopening or a resolution.

    ``items`` are the items a ``changes`` verdict on the whole change names to
    rebuild. ``findings`` are written under a review or a self-review.
    """

    kind: RecordKind
    date: datetime.date
    verdict: Verdict | None
    text: str
    index: int
    items: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()
    who: str | None = None
    fingerprint: str | None = None
    covers: tuple[str, ...] | None = None
    """The items an ``(accepted)`` record covers; None when it names none."""


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
    delegate: bool
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
        """An archived item's review level: its tag, or the project default."""
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
    review_records: tuple[ReviewRecord, ...] = ()
    review_section: Section | None = None
    log: tuple[ReviewRecord, ...] = ()
    """Every record in the Log section, in order; empty in a format 1 task list."""
    version: int = 1
    """The record format the task list was read in."""
    log_section: Section | None = None

    def item(self, number: str) -> Item | None:
        return next((item for item in self.items if item.number == number), None)

    def latest(self, kind: RecordKind) -> ReviewRecord | None:
        """The last record of a kind in the Log, or None."""
        return next((record for record in reversed(self.log) if record.kind is kind), None)


@dataclass
class _Draft:
    """An item while its lines are still being read."""

    number: str
    section: int
    title: str
    ticked: bool
    level_tag: ReviewLevel | None
    delegate: bool
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

    def finish(self, version: int) -> Item:
        def single(label: str) -> str | None:
            return "\n".join(self.fields[label]).strip() if label in self.fields else None

        if version >= LATEST_FORMAT:
            blocked, spec_gap = _open_stoppers(self.records)
            notes = tuple(r.text for r in self.records if r.kind is RecordKind.NOTE)
        else:
            blocked, spec_gap = single(BLOCKED), single(SPEC_GAP)
            notes = tuple("\n".join(note).strip() for note in self.notes)
        return Item(
            number=self.number,
            section=self.section,
            title=self.title,
            ticked=self.ticked,
            level_tag=self.level_tag,
            delegate=self.delegate,
            criteria=single("Criteria"),
            verify=single("Verify"),
            repo=single("Repo"),
            blocked=blocked,
            spec_gap=spec_gap,
            notes=notes,
            records=tuple(self.records),
            index=self.index,
            end=self.end,
            spans=dict(self.spans),
        )


def _open_stoppers(records: list[ReviewRecord]) -> tuple[str | None, str | None]:
    """The blocker and the spec gap that no later ``(resolved)`` record closed."""
    blocked: str | None = None
    spec_gap: str | None = None
    for record in records:
        if record.kind is RecordKind.BLOCKED:
            blocked = record.text
        elif record.kind is RecordKind.GAP:
            spec_gap = record.text
        elif record.kind is RecordKind.RESOLVED:
            blocked = spec_gap = None
    return blocked, spec_gap


def _from_record(record: records.Record, index: int) -> ReviewRecord:
    """A parsed record, as the task list keeps it."""
    is_acceptance = record.kind is RecordKind.ACCEPTED
    return ReviewRecord(
        kind=record.kind,
        date=record.date,
        verdict=record.verdict,
        text=record.text or "",
        index=index,
        items=() if is_acceptance else (record.items or ()),
        who=record.who,
        fingerprint=record.fingerprint,
        covers=record.items if is_acceptance else None,
    )


_OLD_FORMAT = (
    'This line is in the old record format. Run "wm update" to migrate the record; '
    'wm writes records as "(<kind>) YYYY-MM-DD [<args>] [by <who>]: <text>".'
)


class _Parser:
    def __init__(self, doc: Document, version: int) -> None:
        self.doc = doc
        self.version = version
        self.problems: list[Problem] = []
        self.sections: list[TaskSection] = []
        self.items: list[Item] = []
        self.draft: _Draft | None = None
        self.review_records: list[ReviewRecord] = []
        self.review_section: Section | None = None
        self.log: list[ReviewRecord] = []
        self.log_section: Section | None = None

    @property
    def latest(self) -> bool:
        return self.version >= LATEST_FORMAT

    def problem(self, index: int, code: str, message: str) -> None:
        self.problems.append(Problem(self.doc.path, index + 1, code, message))

    def close_item(self) -> None:
        if self.draft is not None:
            self.items.append(self.draft.finish(self.version))
            self.draft = None

    def item_record(self, index: int, text: str) -> None:
        """Read a record under an item, in the latest format."""
        draft = self.draft
        assert draft is not None
        found = records.parse(text)
        if isinstance(found, records.ParseError):
            self.problem(index, "malformed-record", found.message)
            return
        assert found is not None
        if records.KINDS[found.kind].level is records.Level.CHANGE:
            self.problem(
                index,
                "misplaced-record",
                f'A "({found.kind.value})" record is about the whole change, so it goes in '
                f"the {LOG_SECTION} section at the end of the task list.",
            )
            return
        draft.records.append(_from_record(found, index))

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
        if self.latest:
            if labeled and labeled.group(1) in _OLD_LABELS:
                self.problem(index, "old-record-format", _OLD_FORMAT)
            elif labeled:
                self.labeled(index, labeled.group(1), (labeled.group(2) or "").strip())
            elif records.looks_like_record(text):
                self.item_record(index, text)
            else:
                self.problem(
                    index,
                    "unrecognized-item-line",
                    'A line under an item starts with "Criteria:", "Verify:" or "Repo:", or '
                    "is a record that wm writes. Label this line, or write a note with "
                    '"wm note".',
                )
            return
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

    def tags(self, index: int, title: str) -> tuple[str, ReviewLevel | None, bool]:
        """Strip the trailing `review:` and `build:` tags, in either order, from a title."""
        level_tag: ReviewLevel | None = None
        delegate = False
        seen: set[str] = set()
        while tag := _TAG.search(title):
            title = title[: tag.start()].rstrip()
            name, value = tag.group(1), tag.group(2)
            if name in seen:
                self.problem(
                    index,
                    "repeated-tag",
                    f'The "{name}:" tag appears twice on this item. Keep one.',
                )
                continue
            seen.add(name)
            if name == "build":
                if value == DELEGATE:
                    delegate = True
                else:
                    self.problem(
                        index,
                        "unknown-build-tag",
                        f'"{value}" is not a build tag. The only value is: {DELEGATE}.',
                    )
            elif value in set(ReviewLevel):
                level_tag = ReviewLevel(value)
            else:
                levels = ", ".join(level.value for level in ReviewLevel)
                self.problem(
                    index,
                    "unknown-review-level",
                    f'"{value}" is not a review level. Use one of: {levels}.',
                )
        return title, level_tag, delegate

    def item_line(self, index: int, section: TaskSection | None, text: str) -> bool:
        match = _ITEM.match(text)
        if match is None:
            return False
        self.close_item()
        title, level_tag, delegate = self.tags(index, match.group(4))
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
            delegate=delegate,
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

    def change_record(self, index: int, text: str) -> ReviewRecord | None:
        """Read one record line of the Review section."""
        review = _CHANGE_REVIEW.match(text)
        self_review = _SELF_REVIEW.match(text)
        resolved = _RESOLVED.match(text)
        match = review or self_review or resolved
        if match is None:
            self.problem(
                index,
                "malformed-evidence",
                f"This review record doesn't follow the format. Write it as {_CHANGE_FORMATS}.",
            )
            return None
        date = self.date(index, match.group(1))
        if date is None:
            return None
        if self_review:
            return ReviewRecord(RecordKind.SELF_REVIEW, date, None, self_review.group(2), index)
        if resolved:
            return ReviewRecord(RecordKind.RESOLVED, date, None, resolved.group(2), index)
        assert review is not None
        verdict = Verdict(review.group(2))
        items = tuple(review.group(3).split())
        if verdict is Verdict.CHANGES and not items:
            self.problem(
                index,
                "changes-without-items",
                'A "changes" verdict names the items to rebuild: '
                '"(review) YYYY-MM-DD changes 1.2 2.1: <reasons>".',
            )
        elif verdict is not Verdict.CHANGES and items:
            self.problem(
                index,
                "items-without-changes",
                f'Only a "changes" verdict names items. Remove them from this "{verdict}" verdict.',
            )
        return ReviewRecord(RecordKind.REVIEW, date, verdict, review.group(4), index, items)

    def finding(self, index: int, text: str, records: list[ReviewRecord]) -> None:
        """Add a finding line to the record above it."""
        match = _FINDING.match(text)
        last = records[-1] if records else None
        if match is None:
            self.problem(
                index,
                "malformed-finding",
                f"A finding under a review is written {_FINDING_FORMAT}.",
            )
            return
        if last is None or last.kind not in (RecordKind.REVIEW, RecordKind.SELF_REVIEW):
            self.problem(
                index,
                "misplaced-finding",
                "A finding goes under a review or a self-review. Move it, or remove it.",
            )
            return
        finding = Finding(ReviewSeverity(match.group(1)), match.group(2), match.group(3), index)
        records[-1] = ReviewRecord(
            last.kind,
            last.date,
            last.verdict,
            last.text,
            last.index,
            last.items,
            (*last.findings, finding),
        )

    def review(self, section: Section) -> None:
        """Read the Review section: the change's review records and their findings."""
        self.review_section = section
        records: list[ReviewRecord] = []
        for index in range(section.body_start, section.end):
            line = self.doc.lines[index]
            if line.is_blank or line.in_fence:
                continue
            field_match = _FIELD.match(line.text)
            record_match = _RECORD_LINE.match(line.text)
            if record_match:
                record = self.change_record(index, record_match.group(1).strip())
                if record is not None:
                    records.append(record)
            elif field_match:
                self.finding(index, field_match.group(1).strip(), records)
            else:
                self.problem(
                    index,
                    "unrecognized-review-line",
                    f"The Review section holds only records, written {_CHANGE_FORMATS}, and "
                    f"findings under them, written {_FINDING_FORMAT}. wm writes them.",
                )
        self.review_records = records

    def log_record(self, index: int, text: str, found_records: list[ReviewRecord]) -> None:
        """Read one record line of the Log section."""
        found = records.parse(text)
        if found is None or isinstance(found, records.ParseError):
            message = found.message if found is not None else "This is not a record."
            self.problem(index, "malformed-record", message)
            return
        if records.KINDS[found.kind].level is records.Level.ITEM:
            self.problem(
                index,
                "misplaced-record",
                f'A "({found.kind.value})" record is about one item, so it goes under that item.',
            )
            return
        if found.kind is RecordKind.REVIEW and found.verdict is Verdict.CHANGES and not found.items:
            self.problem(
                index,
                "changes-without-items",
                'A "changes" verdict names the items to rebuild: '
                '"(review) YYYY-MM-DD changes 1.2 2.1 [by <who>]: <reasons>".',
            )
        found_records.append(_from_record(found, index))

    def log_finding(self, index: int, text: str, found_records: list[ReviewRecord]) -> None:
        """Add a finding line to the record above it in the Log."""
        parsed = records.parse_finding(text)
        last = found_records[-1] if found_records else None
        if parsed is None:
            self.problem(
                index,
                "malformed-finding",
                f'A finding under a review is written "  - {records.FINDING_SHAPE}".',
            )
            return
        if last is None or last.kind not in (RecordKind.REVIEW, RecordKind.SELF_REVIEW):
            self.problem(
                index,
                "misplaced-finding",
                "A finding goes under a review or a self-review. Move it, or remove it.",
            )
            return
        finding = Finding(parsed.severity, parsed.place, parsed.text, index)
        found_records[-1] = ReviewRecord(
            last.kind,
            last.date,
            last.verdict,
            last.text,
            last.index,
            last.items,
            (*last.findings, finding),
            last.who,
            last.fingerprint,
            last.covers,
        )

    def log_section_body(self, section: Section) -> None:
        """Read the Log section: the change's records and the findings under them."""
        self.log_section = section
        found_records: list[ReviewRecord] = []
        for index in range(section.body_start, section.end):
            line = self.doc.lines[index]
            if line.is_blank or line.in_fence:
                continue
            field_match = _FIELD.match(line.text)
            record_match = _RECORD_LINE.match(line.text)
            if record_match:
                self.log_record(index, record_match.group(1).strip(), found_records)
            elif field_match:
                self.log_finding(index, field_match.group(1).strip(), found_records)
            else:
                self.problem(
                    index,
                    "unrecognized-log-line",
                    f"The {LOG_SECTION} section holds only the records wm writes, each "
                    '"- (<kind>) YYYY-MM-DD [<args>] [by <who>]: <text>", and findings under '
                    f'reviews, each "  - {records.FINDING_SHAPE}".',
                )
        self.log = found_records
        self.review_records = [r for r in found_records if r.kind in _REVIEW_KINDS]

    def latest_sections(self, sections: tuple[Section, ...]) -> None:
        """Read the task sections and the Log section of a task list in the latest format."""
        for section in sections:
            title = section.title.strip().casefold()
            if title == LOG_SECTION.casefold():
                if self.log_section is not None:
                    self.problem(
                        section.start,
                        "duplicate-log-section",
                        f"A task list has one {LOG_SECTION} section. Merge them.",
                    )
                    continue
                self.log_section_body(section)
                continue
            if title == REVIEW_SECTION.casefold():
                self.problem(section.start, "old-record-format", _OLD_FORMAT)
                continue
            if self.log_section is not None:
                self.problem(
                    section.start,
                    "log-section-last",
                    f"The {LOG_SECTION} section comes after every task section. Move this "
                    "section above it.",
                )
            task_section = self.section(section)
            for index in range(section.body_start, section.end):
                self.body_line(index, task_section)
            self.close_item()

    def check_review_items(self) -> None:
        numbers = {item.number for item in self.items}
        for record in self.review_records:
            unknown = [number for number in record.items if number not in numbers]
            if unknown:
                self.problem(
                    record.index,
                    "unknown-item",
                    f"This verdict names {', '.join(unknown)}, which the task list doesn't "
                    "have. Name the change's own items.",
                )

    def parse(self) -> Tasks:
        doc = self.doc
        sections = doc.sections(2)
        first = sections[0].start if sections else len(doc.lines)
        for index in range(first):
            self.body_line(index, None)
        self.close_item()
        if self.latest:
            self.latest_sections(sections)
            sections = ()
        for section in sections:
            if section.title.strip().casefold() == REVIEW_SECTION.casefold():
                if self.review_section is not None:
                    self.problem(
                        section.start,
                        "duplicate-review-section",
                        "A task list has one Review section. Merge them.",
                    )
                    continue
                self.review(section)
                continue
            if self.review_section is not None:
                self.problem(
                    section.start,
                    "review-section-last",
                    "The Review section comes after every task section. Move this section "
                    "above it.",
                )
            task_section = self.section(section)
            for index in range(section.body_start, section.end):
                self.body_line(index, task_section)
            self.close_item()
        self.check_numbering()
        self.check_fields()
        self.check_review_items()
        return Tasks(
            doc,
            tuple(self.sections),
            tuple(self.items),
            tuple(self.problems),
            tuple(self.review_records),
            self.review_section,
            tuple(self.log),
            self.version,
            self.log_section,
        )


def parse_finding(text: str) -> tuple[ReviewSeverity, str, str] | None:
    """A finding written "<severity>: <place>: <text>", or None when it isn't one."""
    match = _FINDING.match(text.strip())
    if match is None:
        return None
    return ReviewSeverity(match.group(1)), match.group(2), match.group(3)


FINDING_FORMAT = "<critical|warning|suggestion>: <place>: <text>"


def parse_tasks(doc: Document, version: int = 1) -> Tasks:
    """Read a task list in the given record format."""
    return _Parser(doc, version).parse()


def is_evidence_line(text: str) -> bool:
    """Whether a line under an item is gate evidence: a blocker, a spec gap or a record."""
    match = _FIELD.match(text)
    if match is None:
        return False
    content = match.group(1)
    return (
        content.startswith((f"{BLOCKED}:", f"{SPEC_GAP}:"))
        or _EVIDENCE.match(content) is not None
        or records.looks_like_record(content)
    )

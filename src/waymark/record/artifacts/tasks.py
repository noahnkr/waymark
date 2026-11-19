"""Task lists: numbered sections of checkbox items, then the change's Log.

An item's definition is its number, title, build tag, criteria, verification and
repo. Its evidence is its tick and the records under it: blockers, spec gaps,
notes, reopenings and resolutions. The records about the whole change, with the
findings under its reviews, sit in a ``## Log`` section at the end. Every record
is read through ``record/evidence/records.py``.
"""

import datetime
import re
from dataclasses import dataclass, field

from waymark.record.evidence import records
from waymark.record.evidence.records import RecordKind
from waymark.record.markdown import labels
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import Document, Section
from waymark.record.terms import ReviewSeverity, Verdict

LOG_SECTION = "Log"
DELEGATE = "delegate"
PLANNER = "planner"
BUILD_VALUES = (PLANNER, DELEGATE)

_SECTION = re.compile(r"^(\d+)\.\s+(\S.*)$")
_ITEM = re.compile(r"^- \[([ xX])\] (\d+)\.(\d+)\s+(\S.*?)\s*$")
_LIST_LINE = re.compile(r"^(?:[-*+]|\d+[.)])(?:\s|$)")
_FIELD = re.compile(r"^  [-*] (\S.*)$")
_ITEM_LABELS = (labels.CRITERIA, labels.VERIFY, labels.REPO, labels.BUILD)
BUILD = labels.BUILD
_RECORD_LINE = re.compile(r"^[-*] (\(.*)$")
_REVIEW_KINDS = (RecordKind.REVIEW, RecordKind.SELF_REVIEW, RecordKind.RESOLVED)


@dataclass(frozen=True)
class Finding:
    """One finding of a review: how much it matters, where, and what."""

    severity: ReviewSeverity
    place: str
    text: str
    index: int


@dataclass(frozen=True)
class ReviewRecord:
    """One record, as the task list keeps it, with the line it is on.

    ``items`` are the items a ``changes`` verdict names to rebuild, ``covers``
    the items an ``(accepted)`` record covers or a review or self-review was of
    (empty for a review written without ``covers``, which covers every item),
    and ``findings`` the findings written under a review or a self-review.
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
    covers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Item:
    """One task item, with what is written under it.

    ``end`` is the index after the item's last line.
    """

    number: str
    section: int
    title: str
    ticked: bool
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
    build: str | None = None
    """Who builds the item, from its Build line: planner or delegate; None without a known
    value."""


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
    log: tuple[ReviewRecord, ...] = ()
    """Every record in the Log section, in order."""
    review_records: tuple[ReviewRecord, ...] = ()
    """The Log's reviews, self-reviews and resolutions of the review."""
    log_section: Section | None = None

    def item(self, number: str) -> Item | None:
        return next((item for item in self.items if item.number == number), None)

    def latest(self, kind: RecordKind) -> ReviewRecord | None:
        """The last record of a kind in the Log, or None."""
        return next((record for record in reversed(self.log) if record.kind is kind), None)


def _open_stoppers(found: list[ReviewRecord]) -> tuple[str | None, str | None]:
    """The blocker and the spec gap that no later ``(resolved)`` record closed."""
    blocked: str | None = None
    spec_gap: str | None = None
    for record in found:
        if record.kind is RecordKind.BLOCKED:
            blocked = record.text
        elif record.kind is RecordKind.GAP:
            spec_gap = record.text
        elif record.kind is RecordKind.RESOLVED:
            blocked = spec_gap = None
    return blocked, spec_gap


def _milestone_record(kind: RecordKind) -> str:
    return (
        f'A "({kind.value})" record is about a milestone\'s roadmap, so it goes in the '
        "milestone's Log, where wm writes it. Remove it from the task list."
    )


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
        covers=(record.items or ()) if is_acceptance else (record.covers or ()),
    )


@dataclass
class _Draft:
    """An item while its lines are still being read."""

    number: str
    section: int
    title: str
    ticked: bool
    delegate: bool
    index: int
    end: int
    fields: dict[str, list[str]] = field(default_factory=dict)
    records: list[ReviewRecord] = field(default_factory=list)
    open_text: list[str] | None = None

    def finish(self) -> Item:
        def single(label: str) -> str | None:
            return "\n".join(self.fields[label]).strip() if label in self.fields else None

        blocked, spec_gap = _open_stoppers(self.records)
        return Item(
            number=self.number,
            section=self.section,
            title=self.title,
            ticked=self.ticked,
            delegate=self.delegate,
            build=build if (build := single(BUILD)) in BUILD_VALUES else None,
            criteria=single("Criteria"),
            verify=single("Verify"),
            repo=single("Repo"),
            blocked=blocked,
            spec_gap=spec_gap,
            notes=tuple(r.text for r in self.records if r.kind is RecordKind.NOTE),
            records=tuple(self.records),
            index=self.index,
            end=self.end,
        )


class _Parser:
    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.problems: list[Problem] = []
        self.sections: list[TaskSection] = []
        self.items: list[Item] = []
        self.draft: _Draft | None = None
        self.log: list[ReviewRecord] = []
        self.log_section: Section | None = None

    def problem(self, index: int, code: str, message: str) -> None:
        self.problems.append(Problem(self.doc.path, index + 1, code, message))

    def close_item(self) -> None:
        if self.draft is not None:
            self.items.append(self.draft.finish())
            self.draft = None

    def item_record(self, index: int, text: str) -> None:
        """Read a record under an item."""
        draft = self.draft
        assert draft is not None
        found = records.parse(text)
        if isinstance(found, records.ParseError):
            self.problem(index, "malformed-record", found.message)
            return
        assert found is not None
        if records.KINDS[found.kind].level is records.Level.MILESTONE:
            self.problem(index, "misplaced-record", _milestone_record(found.kind))
            return
        if records.KINDS[found.kind].level is records.Level.CHANGE:
            self.problem(
                index,
                "misplaced-record",
                f'A "({found.kind.value})" record is about the whole change, so it goes in '
                f"the {LOG_SECTION} section at the end of the task list.",
            )
            return
        draft.records.append(_from_record(found, index))

    def labeled(self, index: int, label: str, value: str) -> None:
        draft = self.draft
        assert draft is not None
        if label in draft.fields:
            self.problem(
                index,
                "duplicate-field",
                f'"{label_line(label)}" appears twice under this item. Keep one.',
            )
            return
        if label == BUILD:
            if draft.delegate:
                self.problem(
                    index,
                    "repeated-tag",
                    f'The item says "build" twice. Keep the "{label_line(BUILD)}" line.',
                )
            elif value == DELEGATE:
                draft.delegate = True
            elif value not in BUILD_VALUES:
                self.problem(
                    index,
                    "unknown-build-tag",
                    f'"{value}" is not a build value. The values are: {PLANNER} and {DELEGATE}.',
                )
            draft.fields[label] = [value]
            return
        draft.fields[label] = [value]
        draft.open_text = draft.fields[label]

    def field_line(self, index: int, text: str) -> None:
        draft = self.draft
        assert draft is not None
        draft.open_text = None
        draft.end = index + 1
        labeled = labels.read_label(text)
        if labeled and not labeled.bullet and labeled.name in _ITEM_LABELS:
            self.labeled(index, labeled.name, labeled.value)
        elif records.looks_like_record(text):
            self.item_record(index, text)
        else:
            self.problem(
                index,
                "unrecognized-item-line",
                "A line under an item starts with "
                + ", ".join(f'"{label_line(label)}"' for label in _ITEM_LABELS)
                + ", or is a record that wm writes. Label this line, or write a note with "
                '"wm note".',
            )

    def item_line(self, index: int, section: TaskSection | None, text: str) -> bool:
        match = _ITEM.match(text)
        if match is None:
            return False
        self.close_item()
        title = match.group(4)
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
            delegate=False,
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
                draft.open_text.append(text.strip())
                draft.end = index + 1
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
            draft.open_text.append(text.strip())
            draft.end = index + 1
        else:
            self.problem(
                index,
                "unrecognized-item-line",
                "Lines under an item are a list indented by two spaces, such as "
                f'"  {label_line(labels.CRITERIA, "...")}". Fix the indentation, or label the '
                "line.",
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
                labels.CRITERIA: item.criteria,
                labels.VERIFY: item.verify,
                labels.REPO: item.repo,
            }
            for label, value in values.items():
                if value is not None and not value:
                    self.problem(
                        item.index,
                        "empty-field",
                        f'"{label_line(label)}" under item {item.number} is empty. '
                        "Write it, or remove the line.",
                    )

    def log_record(self, index: int, text: str) -> None:
        """Read one record line of the Log section."""
        found = records.parse(text)
        if found is None or isinstance(found, records.ParseError):
            message = found.message if found is not None else "This is not a record."
            self.problem(index, "malformed-record", message)
            return
        if records.KINDS[found.kind].level is records.Level.MILESTONE:
            self.problem(index, "misplaced-record", _milestone_record(found.kind))
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
        self.log.append(_from_record(found, index))

    def log_finding(self, index: int, text: str) -> None:
        """Add a finding line to the record above it in the Log."""
        parsed = records.parse_finding(text)
        last = self.log[-1] if self.log else None
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
        self.log[-1] = ReviewRecord(
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

    def log_body(self, section: Section) -> None:
        """Read the Log section: the change's records and the findings under them."""
        self.log_section = section
        for index in range(section.body_start, section.end):
            line = self.doc.lines[index]
            if line.is_blank or line.in_fence:
                continue
            field_match = _FIELD.match(line.text)
            record_match = _RECORD_LINE.match(line.text)
            if record_match:
                self.log_record(index, record_match.group(1).strip())
            elif field_match:
                self.log_finding(index, field_match.group(1).strip())
            else:
                self.problem(
                    index,
                    "unrecognized-log-line",
                    f"The {LOG_SECTION} section holds only the records wm writes, each "
                    '"- (<kind>) YYYY-MM-DD [<args>] [by <who>]: <text>", and findings under '
                    f'reviews, each "  - {records.FINDING_SHAPE}".',
                )

    def check_named_items(self) -> None:
        numbers = {item.number for item in self.items}
        for record in self.log:
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
                self.log_body(section)
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
        self.check_numbering()
        self.check_fields()
        self.check_named_items()
        return Tasks(
            doc,
            tuple(self.sections),
            tuple(self.items),
            tuple(self.problems),
            tuple(self.log),
            tuple(r for r in self.log if r.kind in _REVIEW_KINDS),
            self.log_section,
        )


def parse_tasks(doc: Document) -> Tasks:
    """Read a task list."""
    return _Parser(doc).parse()

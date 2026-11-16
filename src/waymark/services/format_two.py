"""The migration from record format 1 to 2: wm's lines become records in the Log.

wm reads only format 2, so this migration reads the old files as text, with
its own few patterns. For every change, active and archived:

- ``Blocked:``, ``Spec gap:`` and ``Note:`` lines under items become
  ``(blocked)``, ``(gap)`` and ``(note)`` records;
- a review record under an item becomes a ``(note)`` record that keeps its
  date and says what it was, and a ``review:`` tag on an item goes;
- the ``## Review`` section becomes the ``## Log``, its findings with the place
  in backticks;
- the proposal's ``Accepted:`` and ``Synced:`` lines move to the top of the Log,
  and a ``Review override:`` line, in the proposal or its outcome, to its end.

An acceptance keeps its date, who and digest, and names every item when the old
line named none; the digest no longer matches the new fingerprint, so an active
change is accepted again. A line without a date takes the date of the last
commit that touched its file, or today when the file isn't committed.
"""

import datetime
import functools
import re
from collections.abc import Callable

from waymark.record import git, records
from waymark.record.files import RecordFiles
from waymark.record.names import parse_archive_name
from waymark.record.project import RECORD_DIR
from waymark.record.records import RecordKind
from waymark.record.store import Transaction
from waymark.record.terms import ReviewSeverity, Verdict

CHANGES = "changes"
ARCHIVE = "archive"
PROPOSAL = "proposal.md"
TASKS = "tasks.md"
LOG_HEADING = "## Log"

_ACCEPTED = re.compile(
    r"^Accepted: (\d{4}-\d{2}-\d{2}) by (.+?) "
    r"\(fingerprint: ([0-9a-f]{16})(?:; items: (\d+\.\d+(?: \d+\.\d+)*))?\)\s*$"
)
_SYNCED = re.compile(r"^Synced: (\d{4}-\d{2}-\d{2})\s*$")
_OVERRIDE = re.compile(r"^Review override: (\S.*?)\s*$")
_ITEM = re.compile(r"^- \[[ xX]\] (\d+\.\d+)\s")
_REVIEW_TAG = re.compile(r"\s+`review:\s*[A-Za-z-]+`")
_HEADING = re.compile(r"^##\s+(.*?)\s*$")
_OLD_LABELED = re.compile(r"^  [-*] (Blocked|Spec gap|Note):\s*(.*?)\s*$")
_CONTINUATION = re.compile(r"^ {3,}\S")
_ITEM_REVIEW = re.compile(
    r"^  [-*] \(review\) (\d{4}-\d{2}-\d{2}) (pass|changes|spec-gap)((?: \d+\.\d+)*): (.*?)\s*$"
)
_ITEM_SELF_REVIEW = re.compile(r"^  [-*] \(self-review\) (\d{4}-\d{2}-\d{2}): (.*?)\s*$")
_OLD_FINDING = re.compile(r"^(\s+[-*] )(critical|warning|suggestion): (\S.*?): (\S.*?)\s*$")
_KINDS = {"Blocked": RecordKind.BLOCKED, "Spec gap": RecordKind.GAP, "Note": RecordKind.NOTE}

Dating = Callable[[], datetime.date]


def migrate_to_format_2(files: RecordFiles, transaction: Transaction) -> None:
    """Stage the format 2 text of every change, active and archived."""
    repository = files.root.parent
    dates: dict[str, datetime.date] = {}

    def date_of(path: str) -> datetime.date:
        if path not in dates:
            key = f"{RECORD_DIR}/{path}"
            when = git.last_changed(repository, [key]).get(key)
            dates[path] = when.date() if when else datetime.date.today()
        return dates[path]

    for folder, archived_on in _change_folders(files):
        tasks_path, proposal_path = f"{folder}/{TASKS}", f"{folder}/{PROPOSAL}"
        tasks = files.read(tasks_path, []) if files.is_file(tasks_path) else None
        proposal = files.read(proposal_path, []) if files.is_file(proposal_path) else None
        numbers = [m.group(1) for line in (tasks or "").splitlines() if (m := _ITEM.match(line))]
        first: list[str] = []
        last: list[str] = []
        if proposal is not None:
            override_day = archived_on or date_of(proposal_path)
            kept, first, last = _proposal(proposal, numbers, override_day)
            if kept != proposal:
                transaction.write(proposal_path, kept)
        if tasks is not None:
            migrated = _tasks(tasks, first, last, functools.partial(date_of, tasks_path))
            if migrated != tasks:
                transaction.write(tasks_path, migrated)


def _change_folders(files: RecordFiles) -> list[tuple[str, datetime.date | None]]:
    """Every change folder, with the date it was archived on, if it was."""
    folders: list[tuple[str, datetime.date | None]] = []
    for entry in files.entries(CHANGES):
        if entry.is_dir and entry.name != ARCHIVE:
            folders.append((f"{CHANGES}/{entry.name}", None))
    for entry in files.entries(f"{CHANGES}/{ARCHIVE}"):
        parsed = parse_archive_name(entry.name) if entry.is_dir else None
        if parsed is not None:
            folders.append((f"{CHANGES}/{ARCHIVE}/{entry.name}", parsed.date))
    return folders


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _lines(text: str) -> list[str]:
    """The text's lines, each with its line ending, the last one given one if it lacks it."""
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += _newline(text)
    return lines


def _proposal(
    text: str, numbers: list[str], override_day: datetime.date
) -> tuple[str, list[str], list[str]]:
    """The proposal without wm's old lines, and the records for the top and end of the Log."""
    first: list[str] = []
    last: list[str] = []
    kept: list[str] = []
    for line in _lines(text):
        bare = line.rstrip("\r\n")
        accepted = _ACCEPTED.match(bare)
        synced = _SYNCED.match(bare)
        override = _OVERRIDE.match(bare)
        if accepted:
            items = tuple(accepted.group(4).split()) if accepted.group(4) else tuple(numbers)
            entry = records.Record(
                RecordKind.ACCEPTED,
                datetime.date.fromisoformat(accepted.group(1)),
                who=accepted.group(2).strip() or None,
                fingerprint=accepted.group(3),
                items=items,
            )
            first.append(records.render(entry))
        elif synced:
            day = datetime.date.fromisoformat(synced.group(1))
            first.append(records.render(records.Record(RecordKind.SYNCED, day)))
        elif override:
            entry = records.Record(RecordKind.OVERRIDE, override_day, text=override.group(1))
            last.append(records.render(entry))
        else:
            kept.append(line)
    while len(kept) > 1 and not kept[-1].strip():
        kept.pop()
    return "".join(kept), first, last


def _item_review(line: str) -> str | None:
    """A review record under an item, as the note that keeps it; None when it isn't one."""
    review = _ITEM_REVIEW.match(line)
    if review:
        text = f"review {Verdict(review.group(2)).value}{review.group(3)}: {review.group(4)}"
        day = datetime.date.fromisoformat(review.group(1))
        return records.render(records.Record(RecordKind.NOTE, day, text=text))
    self_review = _ITEM_SELF_REVIEW.match(line)
    if self_review:
        day = datetime.date.fromisoformat(self_review.group(1))
        text = f"self-review: {self_review.group(2)}"
        return records.render(records.Record(RecordKind.NOTE, day, text=text))
    return None


def _log_line(line: str, newline: str) -> str:
    """A line of the old Review section: findings take the backticked place."""
    finding = _OLD_FINDING.match(line.rstrip("\r\n"))
    if finding is None:
        return line
    parsed = records.Finding(ReviewSeverity(finding.group(2)), finding.group(3), finding.group(4))
    return f"{finding.group(1)}{records.render_finding(parsed)}{newline}"


def _tasks(text: str, first: list[str], last: list[str], day: Dating) -> str:
    """The task list in format 2, with the moved records at the top and end of its Log."""
    lines = _lines(text)
    newline = _newline(text)
    out: list[str] = []
    in_log = False
    index = 0
    while index < len(lines):
        line = lines[index]
        bare = line.rstrip("\r\n")
        index += 1
        heading = _HEADING.match(bare)
        if heading:
            in_log = heading.group(1).casefold() in ("review", "log")
            out.append(f"{LOG_HEADING}{newline}" if in_log else line)
        elif in_log:
            out.append(_log_line(line, newline))
        elif _ITEM.match(bare):
            out.append(_REVIEW_TAG.sub("", bare) + newline)
        elif old := _OLD_LABELED.match(bare):
            parts = [old.group(2)]
            while index < len(lines) and _CONTINUATION.match(lines[index]):
                parts.append(lines[index].strip())
                index += 1
            body = " ".join(part for part in parts if part) or "(no text)"
            entry = records.Record(_KINDS[old.group(1)], day(), text=body)
            out.append(f"  - {records.render(entry)}{newline}")
        else:
            note = _item_review(bare)
            out.append(f"  - {note}{newline}" if note is not None else line)
    return _with_log(out, first, last, newline)


def _with_log(lines: list[str], first: list[str], last: list[str], newline: str) -> str:
    """Put the moved records at the top and end of the Log, adding the Log when there is none."""
    if not first and not last:
        return "".join(lines)
    heading = f"{LOG_HEADING}{newline}"
    while lines and not lines[-1].strip():
        lines.pop()
    if heading not in lines:
        lines += [newline, heading]
    at = lines.index(heading) + 1
    body = [line for line in lines[at:] if line.strip()]
    records_block = [f"- {record}{newline}" for record in first]
    records_block += body
    records_block += [f"- {record}{newline}" for record in last]
    return "".join([*lines[:at], newline, *records_block])

"""Records: the dated lines wm writes into a change as evidence.

Every record has one shape, ``(<kind>) <YYYY-MM-DD> [<args>] [by <who>]: <text>``.
The kind's arguments come first, so ``by`` can run to ``: `` or the end of the
line and the name may hold spaces. A kind without text ends after who wrote it.
This module is the only place a record's text is built or read; the table of
kinds says what each one carries.

Findings sit under a review record as ``<severity> `<place>`: <text>``.
"""

import datetime
import re
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path

from waymark.record import git
from waymark.record.names import is_valid_name
from waymark.record.terms import ReviewSeverity, Verdict

IMPLEMENTER = "wm-implementer"
"""Who wrote a record taken from an implementer's ending."""
REVIEWER = "wm-reviewer"
"""Who wrote a record taken from a reviewer's ending."""


class RecordError(ValueError):
    """A value that can't go into a record, with the reason."""


class RecordKind(StrEnum):
    """The kinds of record wm writes."""

    ACCEPTED = "accepted"
    SYNCED = "synced"
    OVERRIDE = "override"
    SELF_REVIEW = "self-review"
    REVIEW = "review"
    RESOLVED = "resolved"
    REOPENED = "reopened"
    BLOCKED = "blocked"
    GAP = "gap"
    NOTE = "note"
    ADDED = "added"
    DROPPED = "dropped"
    MOVED = "moved"
    PROPOSED = "proposed"
    ARCHIVED = "archived"


class Level(Enum):
    """Where a kind of record goes: under an item, in the change's Log, either, or in a
    milestone's Log."""

    ITEM = "item"
    CHANGE = "change"
    BOTH = "both"
    MILESTONE = "milestone"


class Grammar(Enum):
    """The arguments a kind of record carries before who wrote it."""

    NONE = "none"
    VERDICT = "verdict"
    """A verdict, the item numbers a ``changes`` verdict names, then optionally ``covers``."""
    COVERS = "covers"
    """Optionally ``covers <number> <number>...``: the items a review was of."""
    ACCEPTANCE = "acceptance"
    """``fingerprint <hex16>``, then ``items <number> <number>...``."""
    SYNC = "sync"
    """Optionally ``fingerprint <hex16>``: the acceptance stamped again for the merged specs."""
    CHANGE_NAME = "change-name"
    """A change's name: the roadmap line a milestone record is about."""
    MOVE = "move"
    """A change's name, then ``after <change>`` or ``first``: where its roadmap line went."""


@dataclass(frozen=True)
class KindSpec:
    """What one kind of record carries, and its shape for messages."""

    grammar: Grammar
    has_text: bool
    level: Level
    shape: str


KINDS: dict[RecordKind, KindSpec] = {
    RecordKind.ACCEPTED: KindSpec(
        Grammar.ACCEPTANCE,
        has_text=False,
        level=Level.CHANGE,
        shape="(accepted) YYYY-MM-DD fingerprint <digest> items <item> <item>... [by <who>]",
    ),
    RecordKind.SYNCED: KindSpec(
        Grammar.SYNC,
        has_text=False,
        level=Level.CHANGE,
        shape="(synced) YYYY-MM-DD [fingerprint <digest>] [by <who>]",
    ),
    RecordKind.OVERRIDE: KindSpec(
        Grammar.NONE,
        has_text=True,
        level=Level.CHANGE,
        shape="(override) YYYY-MM-DD [by <who>]: <reason>",
    ),
    RecordKind.SELF_REVIEW: KindSpec(
        Grammar.COVERS,
        has_text=True,
        level=Level.CHANGE,
        shape="(self-review) YYYY-MM-DD [covers <item>...] [by <who>]: <summary>",
    ),
    RecordKind.REVIEW: KindSpec(
        Grammar.VERDICT,
        has_text=True,
        level=Level.CHANGE,
        shape=(
            "(review) YYYY-MM-DD pass|changes <item>...|spec-gap [covers <item>...] "
            "[by <who>]: <reasons>"
        ),
    ),
    RecordKind.RESOLVED: KindSpec(
        Grammar.NONE,
        has_text=True,
        level=Level.BOTH,
        shape="(resolved) YYYY-MM-DD [by <who>]: <what was decided>",
    ),
    RecordKind.REOPENED: KindSpec(
        Grammar.NONE, has_text=False, level=Level.ITEM, shape="(reopened) YYYY-MM-DD [by <who>]"
    ),
    RecordKind.BLOCKED: KindSpec(
        Grammar.NONE,
        has_text=True,
        level=Level.ITEM,
        shape="(blocked) YYYY-MM-DD [by <who>]: <reason>",
    ),
    RecordKind.GAP: KindSpec(
        Grammar.NONE,
        has_text=True,
        level=Level.ITEM,
        shape="(gap) YYYY-MM-DD [by <who>]: <what is missing>",
    ),
    RecordKind.NOTE: KindSpec(
        Grammar.NONE, has_text=True, level=Level.ITEM, shape="(note) YYYY-MM-DD [by <who>]: <text>"
    ),
    RecordKind.ADDED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=True,
        level=Level.MILESTONE,
        shape="(added) YYYY-MM-DD <change> [by <who>]: <description>",
    ),
    RecordKind.DROPPED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=True,
        level=Level.MILESTONE,
        shape="(dropped) YYYY-MM-DD <change> [by <who>]: <reason>",
    ),
    RecordKind.MOVED: KindSpec(
        Grammar.MOVE,
        has_text=False,
        level=Level.MILESTONE,
        shape="(moved) YYYY-MM-DD <change> after <change>|first [by <who>]",
    ),
    RecordKind.PROPOSED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=False,
        level=Level.MILESTONE,
        shape="(proposed) YYYY-MM-DD <change> [by <who>]",
    ),
    RecordKind.ARCHIVED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=False,
        level=Level.MILESTONE,
        shape="(archived) YYYY-MM-DD <change> [by <who>]",
    ),
}

_START = re.compile(r"^\(([a-z][a-z-]*)\)(?=\s|$)")
_HEAD = re.compile(r"^\(([a-z][a-z-]*)\) (\d{4}-\d{2}-\d{2})(?=\s|:|$)(.*)$")
_ITEM_NUMBER = re.compile(r"^\d+\.\d+$")
_DIGEST = re.compile(r"^[0-9a-f]{16}$")
_TEXT_SEPARATOR = ": "


@dataclass(frozen=True)
class Record:
    """One record. Only the fields its kind's grammar has are set."""

    kind: RecordKind
    date: datetime.date
    who: str | None = None
    text: str | None = None
    verdict: Verdict | None = None
    items: tuple[str, ...] | None = None
    """The items a ``changes`` verdict names, or an acceptance covers; None when absent."""
    fingerprint: str | None = None
    covers: tuple[str, ...] | None = None
    """The items a review or a self-review was of; None when absent, which covers every item."""
    change: str | None = None
    """The change whose roadmap line a milestone record is about."""
    after: str | None = None
    """For ``(moved)``, the change the line went after; None when it went first."""


@dataclass(frozen=True)
class ParseError:
    """A line that starts like a record but doesn't have a record's shape."""

    kind: RecordKind | None
    message: str


def shape(kind: RecordKind) -> str:
    """The shape of a kind of record, as messages show it."""
    return KINDS[kind].shape


def looks_like_record(text: str) -> bool:
    """Whether a line's text starts like a record: a lowercase word in parentheses."""
    return _START.match(text) is not None


def _arguments(record: Record) -> list[str]:  # noqa: PLR0911 - one return per grammar
    grammar = KINDS[record.kind].grammar
    if grammar is Grammar.VERDICT:
        assert record.verdict is not None
        return [record.verdict.value, *(record.items or ()), *_covers_words(record)]
    if grammar is Grammar.COVERS:
        return _covers_words(record)
    if grammar is Grammar.SYNC:
        return ["fingerprint", record.fingerprint] if record.fingerprint else []
    if grammar is Grammar.ACCEPTANCE:
        assert record.fingerprint is not None
        parts = ["fingerprint", record.fingerprint]
        if record.items is not None:
            parts += ["items", *record.items]
        return parts
    if grammar is Grammar.CHANGE_NAME:
        assert record.change is not None
        return [record.change]
    if grammar is Grammar.MOVE:
        assert record.change is not None
        return [record.change, *(["after", record.after] if record.after else ["first"])]
    return []


def _covers_words(record: Record) -> list[str]:
    return ["covers", *record.covers] if record.covers else []


def render(record: Record) -> str:
    """A record's text, without the list marker in front of it."""
    spec = KINDS[record.kind]
    words = [f"({record.kind.value})", record.date.isoformat(), *_arguments(record)]
    if record.who:
        words += ["by", record.who]
    line = " ".join(words)
    if spec.has_text:
        if not record.text:
            raise RecordError(f'A "{record.kind.value}" record needs a text.')
        line += _TEXT_SEPARATOR + record.text
    return line


def _fail(kind: RecordKind | None, reason: str) -> ParseError:
    if kind is None:
        return ParseError(None, reason)
    return ParseError(kind, f'{reason} A "{kind.value}" record is written "{shape(kind)}".')


def parse(text: str) -> Record | ParseError | None:  # noqa: PLR0911 - one return per refusal
    """Read a record from a line's text, without its list marker.

    None when the text doesn't start like a record at all; a ParseError when it
    does but has the wrong shape or an unknown kind.
    """
    text = text.strip()
    start = _START.match(text)
    if start is None:
        return None
    before_text, colon, after_text = text.partition(_TEXT_SEPARATOR)
    text = " ".join(before_text.split()) + colon + after_text
    try:
        kind = RecordKind(start.group(1))
    except ValueError:
        known = ", ".join(f"({k.value})" for k in RecordKind)
        return _fail(None, f'"({start.group(1)})" is not a kind of record. The kinds are {known}.')
    head = _HEAD.match(text)
    if head is None:
        return _fail(kind, "The date is missing or not written YYYY-MM-DD.")
    try:
        date = datetime.date.fromisoformat(head.group(2))
    except ValueError:
        return _fail(kind, f'"{head.group(2)}" is not a date.')
    spec = KINDS[kind]
    rest = head.group(3)
    body, separator, line_text = rest.partition(_TEXT_SEPARATOR)
    if rest.startswith(":") and not rest.startswith(_TEXT_SEPARATOR):
        return _fail(kind, "Put a space after the colon.")
    if spec.has_text and (not separator or not line_text.strip()):
        return _fail(kind, "The text after the colon is missing.")
    if not spec.has_text and separator:
        return _fail(kind, "This kind of record has no text after a colon.")
    words, who = _split_who(body.strip())
    if who == "":
        return _fail(kind, 'The name after "by" is missing.')
    text_value = line_text.strip() if spec.has_text else None
    if spec.grammar in (Grammar.CHANGE_NAME, Grammar.MOVE):
        place = _change_arguments(kind, spec.grammar, words)
        if isinstance(place, ParseError):
            return place
        change, after = place
        return Record(kind, date, who=who, text=text_value, change=change, after=after)
    found = _read_arguments(kind, spec.grammar, words)
    if isinstance(found, ParseError):
        return found
    verdict, items, fingerprint, covers = found
    return Record(
        kind,
        date,
        who=who,
        text=line_text.strip() if spec.has_text else None,
        verdict=verdict,
        items=items,
        fingerprint=fingerprint,
        covers=covers,
    )


def _split_who(body: str) -> tuple[list[str], str | None]:
    """The argument words, and who wrote the record: None when it doesn't say."""
    words = body.split()
    if "by" not in words:
        return words, None
    at = words.index("by")
    return words[:at], " ".join(words[at + 1 :])


_Arguments = tuple[Verdict | None, tuple[str, ...] | None, str | None, tuple[str, ...] | None]


def _read_arguments(
    kind: RecordKind, grammar: Grammar, words: list[str]
) -> _Arguments | ParseError:
    """The arguments before ``by``, read by the kind's grammar."""
    if grammar is Grammar.VERDICT:
        return _verdict_arguments(kind, words)
    if grammar is Grammar.SYNC:
        return _sync_arguments(kind, words)
    if grammar is Grammar.ACCEPTANCE:
        return _acceptance_arguments(kind, words)
    if grammar is Grammar.COVERS:
        covers = _covers_arguments(kind, words)
        return covers if isinstance(covers, ParseError) else (None, None, None, covers)
    if words:
        return _fail(kind, f'"{" ".join(words)}" is not expected before "by" or the colon.')
    return None, None, None, None


def _change_arguments(
    kind: RecordKind, grammar: Grammar, words: list[str]
) -> tuple[str, str | None] | ParseError:
    """A milestone record's change name, and for ``(moved)`` the change it went after."""
    if not words or not is_valid_name(words[0]):
        return _fail(kind, "The change's name is missing or not a valid name.")
    rest = words[1:]
    if grammar is Grammar.CHANGE_NAME:
        if rest:
            return _fail(kind, f'"{" ".join(rest)}" is not expected after the change\'s name.')
        return words[0], None
    if rest == ["first"]:
        return words[0], None
    if len(rest) == 2 and rest[0] == "after" and is_valid_name(rest[1]):  # noqa: PLR2004
        return words[0], rest[1]
    return _fail(kind, 'After the change\'s name comes "after <change>" or "first".')


def _covers_arguments(kind: RecordKind, words: list[str]) -> tuple[str, ...] | ParseError | None:
    """``covers <number> <number>...``, or nothing; the item numbers, or None."""
    if not words:
        return None
    if words[0] != "covers" or not words[1:]:
        return _fail(kind, f'"{" ".join(words)}" is not expected before "by" or the colon.')
    if any(not _ITEM_NUMBER.match(item) for item in words[1:]):
        return _fail(kind, 'Only item numbers such as 1.2 may follow "covers".')
    return tuple(words[1:])


def _verdict_arguments(kind: RecordKind, words: list[str]) -> _Arguments | ParseError:
    if not words:
        return _fail(kind, "The verdict is missing.")
    try:
        verdict = Verdict(words[0])
    except ValueError:
        return _fail(kind, f'"{words[0]}" is not a verdict.')
    rest = words[1:]
    at = rest.index("covers") if "covers" in rest else len(rest)
    items = tuple(rest[:at])
    if any(not _ITEM_NUMBER.match(item) for item in items):
        return _fail(kind, "Only item numbers such as 1.2 may follow the verdict.")
    if items and verdict is not Verdict.CHANGES:
        return _fail(kind, f'Only a "changes" verdict names items, not "{verdict.value}".')
    covers = _covers_arguments(kind, rest[at:])
    if isinstance(covers, ParseError):
        return covers
    return verdict, items if verdict is Verdict.CHANGES else None, None, covers


def _is_fingerprint(words: list[str]) -> bool:
    """Whether the words start with ``fingerprint <hex16>``."""
    return len(words) >= 2 and words[0] == "fingerprint" and bool(_DIGEST.match(words[1]))  # noqa: PLR2004


def _sync_arguments(kind: RecordKind, words: list[str]) -> _Arguments | ParseError:
    if not words:
        return None, None, None, None
    if len(words) != 2 or not _is_fingerprint(words):  # noqa: PLR2004
        return _fail(kind, "Only a fingerprint of 16 hexadecimal digits may follow the date.")
    return None, None, words[1], None


def _acceptance_arguments(kind: RecordKind, words: list[str]) -> _Arguments | ParseError:
    if not _is_fingerprint(words):
        return _fail(kind, "The fingerprint is missing or not 16 hexadecimal digits.")
    rest = words[2:]
    if not rest[1:] or rest[0] != "items" or any(not _ITEM_NUMBER.match(i) for i in rest[1:]):
        return _fail(kind, 'After the fingerprint come "items" and the item numbers.')
    return None, tuple(rest[1:]), words[1], None


@dataclass(frozen=True)
class Finding:
    """One thing a review found: how much it matters, where, and what."""

    severity: ReviewSeverity
    place: str
    text: str


FINDING_SHAPE = "<severity> `<place>`: <text>"
FINDING_ARGUMENT = "<critical|warning|suggestion>: <place>: <text>"

_FINDING = re.compile(r"^(critical|warning|suggestion)\s+`([^`]+)`:\s+(\S.*)$")
_FINDING_ARGUMENT_QUOTED = re.compile(r"^(critical|warning|suggestion): `([^`]+)`: (\S.*)$")
_FINDING_ARGUMENT = re.compile(r"^(critical|warning|suggestion): (\S.*?): (\S.*)$")


def render_finding(finding: Finding) -> str:
    """A finding's text, without the list marker in front of it."""
    if "`" in finding.place:
        raise RecordError("A finding's place can't hold a backtick.")
    return f"{finding.severity.value} `{finding.place}`: {finding.text}"


def parse_finding(text: str) -> Finding | None:
    """Read a finding as wm writes it under a review record; None when it isn't one."""
    match = _FINDING.match(text.strip())
    if match is None:
        return None
    return Finding(ReviewSeverity(match.group(1)), match.group(2), match.group(3).strip())


def parse_finding_argument(text: str) -> Finding | None:
    """Read a finding as a command takes it: ``<severity>: <place>: <text>``.

    A place that holds ``: `` is given in backticks; otherwise it runs to the
    first ``: ``.
    """
    text = text.strip()
    match = _FINDING_ARGUMENT_QUOTED.match(text) or _FINDING_ARGUMENT.match(text)
    if match is None:
        return None
    return Finding(ReviewSeverity(match.group(1)), match.group(2), match.group(3).strip())


def check_who(who: str) -> str:
    """A name fit to go into a record; raises RecordError otherwise."""
    name = " ".join(who.split())
    if not name:
        raise RecordError("The name after --by is empty.")
    if _TEXT_SEPARATOR in name or name.endswith(":"):
        raise RecordError(f'"{name}" can\'t be used as a name: it holds ": ".')
    return name


def who_for(root: Path, by: str | None) -> str | None:
    """Who writes a record: ``--by`` when given, else the git user, else None."""
    if by is not None:
        return check_who(by)
    name = git.user_name(root)
    if name is None:
        return None
    try:
        return check_who(name)
    except RecordError:
        return None

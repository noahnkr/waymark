"""Records: the dated lines wm writes into a change as evidence.

Every record has one shape, ``<YYYY-MM-DD> (<kind>) [<args>] [by <who>]: <text>``.
The kind's arguments come first, so ``by`` can run to ``: `` or the end of the
line and the name may hold spaces. A kind without text ends after who wrote it.
A list of items among the arguments is separated by ``, ``, and a list that
another argument follows ends with ``;``. This module is the only place a
record's text is built or read; the table of kinds says what each one carries.

Findings sit under a review record as ``[<severity>] `<place>`: <text>``.

A line that starts like a record in an older shape, with its kind before its date,
is recognized so that it can be reported, and is never read as a record.
"""

import datetime
import ntpath
import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum, StrEnum
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath

from waymark.record.machine import git
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
    TICKED = "ticked"
    REVISED = "revised"
    ADDED = "added"
    DROPPED = "dropped"
    MOVED = "moved"
    PROPOSED = "proposed"
    ARCHIVED = "archived"


class Level(Enum):
    """Where a kind of record goes: in the change's Log naming an item, in the change's Log
    about the whole change, either, or in a milestone's Log."""

    ITEM = "item"
    CHANGE = "change"
    BOTH = "both"
    MILESTONE = "milestone"
    CHANGE_OR_MILESTONE = "change-or-milestone"
    """In a change's Log about the whole change, or in a milestone's Log naming the change."""


class Grammar(Enum):
    """The arguments a kind of record carries before who wrote it."""

    NONE = "none"
    ITEM = "item"
    """One item number: the item a record is about. A record in the Log names it; one still
    written under its item may leave it out."""
    VERDICT = "verdict"
    """A verdict, the item numbers a ``changes`` verdict names, then optionally ``covers``.

    The verdict's list ends with ``;`` when ``covers`` follows it.
    """
    COVERS = "covers"
    """Optionally ``covers <number>, <number>...``: the items a review was of."""
    ACCEPTANCE = "acceptance"
    """``fingerprint <hex16>``, then ``items <number>, <number>...``."""
    SYNC = "sync"
    """Optionally ``fingerprint <hex16>``: the acceptance stamped again for the merged specs."""
    CHANGE_NAME = "change-name"
    """A change's name: the roadmap line a milestone record is about."""
    MOVE = "move"
    """A change's name, then ``after <change>`` or ``first``: where its roadmap line went."""
    OPTIONAL_CHANGE_NAME = "optional-change-name"
    """A change's name in a milestone's Log, and nothing in the change's own Log."""
    PARTS = "parts"
    """Optionally the parts a revision changed, separated by ``, ``: item numbers,
    ``proposal``, ``design`` or ``specs/<area>``."""


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
        shape="YYYY-MM-DD (accepted) fingerprint <digest> items <item>, <item>... [by <who>]",
    ),
    RecordKind.SYNCED: KindSpec(
        Grammar.SYNC,
        has_text=False,
        level=Level.CHANGE,
        shape="YYYY-MM-DD (synced) [fingerprint <digest>] [by <who>]",
    ),
    RecordKind.OVERRIDE: KindSpec(
        Grammar.NONE,
        has_text=True,
        level=Level.CHANGE,
        shape="YYYY-MM-DD (override) [by <who>]: <reason>",
    ),
    RecordKind.SELF_REVIEW: KindSpec(
        Grammar.COVERS,
        has_text=True,
        level=Level.CHANGE,
        shape="YYYY-MM-DD (self-review) [covers <item>, <item>...] [by <who>]: <summary>",
    ),
    RecordKind.REVIEW: KindSpec(
        Grammar.VERDICT,
        has_text=True,
        level=Level.CHANGE,
        shape=(
            "YYYY-MM-DD (review) pass|changes <item>, <item>...[;]|spec-gap "
            "[covers <item>, <item>...] [by <who>]: <reasons>"
        ),
    ),
    RecordKind.RESOLVED: KindSpec(
        Grammar.ITEM,
        has_text=True,
        level=Level.BOTH,
        shape="YYYY-MM-DD (resolved) [<item>] [by <who>]: <what was decided>",
    ),
    RecordKind.REOPENED: KindSpec(
        Grammar.ITEM,
        has_text=False,
        level=Level.ITEM,
        shape="YYYY-MM-DD (reopened) <item> [by <who>]",
    ),
    RecordKind.BLOCKED: KindSpec(
        Grammar.ITEM,
        has_text=True,
        level=Level.ITEM,
        shape="YYYY-MM-DD (blocked) <item> [by <who>]: <reason>",
    ),
    RecordKind.GAP: KindSpec(
        Grammar.ITEM,
        has_text=True,
        level=Level.ITEM,
        shape="YYYY-MM-DD (gap) <item> [by <who>]: <what is missing>",
    ),
    RecordKind.NOTE: KindSpec(
        Grammar.ITEM,
        has_text=True,
        level=Level.ITEM,
        shape="YYYY-MM-DD (note) <item> [by <who>]: <text>",
    ),
    RecordKind.TICKED: KindSpec(
        Grammar.ITEM,
        has_text=False,
        level=Level.ITEM,
        shape="YYYY-MM-DD (ticked) <item> [by <who>]",
    ),
    RecordKind.REVISED: KindSpec(
        Grammar.PARTS,
        has_text=True,
        level=Level.CHANGE,
        shape="YYYY-MM-DD (revised) [<part>, <part>...] [by <who>]: <why>",
    ),
    RecordKind.ADDED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=True,
        level=Level.MILESTONE,
        shape="YYYY-MM-DD (added) <change> [by <who>]: <description>",
    ),
    RecordKind.DROPPED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=True,
        level=Level.MILESTONE,
        shape="YYYY-MM-DD (dropped) <change> [by <who>]: <reason>",
    ),
    RecordKind.MOVED: KindSpec(
        Grammar.MOVE,
        has_text=False,
        level=Level.MILESTONE,
        shape="YYYY-MM-DD (moved) <change> after <change>|first [by <who>]",
    ),
    RecordKind.PROPOSED: KindSpec(
        Grammar.CHANGE_NAME,
        has_text=False,
        level=Level.MILESTONE,
        shape="YYYY-MM-DD (proposed) <change> [by <who>]",
    ),
    RecordKind.ARCHIVED: KindSpec(
        Grammar.OPTIONAL_CHANGE_NAME,
        has_text=False,
        level=Level.CHANGE_OR_MILESTONE,
        shape="YYYY-MM-DD (archived) [<change>] [by <who>]",
    ),
}

_START = re.compile(r"^\(([a-z][a-z-]*)\)(?=\s|$)")
_DATE_FIRST = re.compile(r"^(\d[\d-]*) \(([a-z][a-z-]*)\)(?=\s|:|$)(.*)$")
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
    item: str | None = None
    """The item a record about one item names; None when it names none."""
    parts: tuple[str, ...] | None = None
    """The parts a ``(revised)`` record names; None when it names none."""


@dataclass(frozen=True)
class ParseError:
    """A line that starts like a record but doesn't have a record's shape."""

    kind: RecordKind | None
    message: str


def shape(kind: RecordKind) -> str:
    """The shape of a kind of record, as messages show it."""
    return KINDS[kind].shape


def looks_like_record(text: str) -> bool:
    """Whether a line's text starts like a record: a lowercase word in parentheses, after a
    date, or first as in the older shape, which is then reported."""
    return _START.match(text) is not None or _DATE_FIRST.match(text) is not None


def _items(numbers: Sequence[str], *, followed: bool = False) -> str:
    """A list of items in a record: separated by commas, ending with ``;`` when another
    argument follows it."""
    return ", ".join(numbers) + (";" if followed else "")


def _arguments(record: Record) -> list[str]:  # noqa: PLR0911 - one return per grammar
    grammar = KINDS[record.kind].grammar
    if grammar is Grammar.ITEM:
        return [record.item] if record.item else []
    if grammar is Grammar.VERDICT:
        assert record.verdict is not None
        listed = [_items(record.items, followed=bool(record.covers))] if record.items else []
        return [record.verdict.value, *listed, *_covers_words(record)]
    if grammar is Grammar.COVERS:
        return _covers_words(record)
    if grammar is Grammar.SYNC:
        return ["fingerprint", record.fingerprint] if record.fingerprint else []
    if grammar is Grammar.ACCEPTANCE:
        assert record.fingerprint is not None
        parts = ["fingerprint", record.fingerprint]
        if record.items is not None:
            parts += ["items", _items(record.items)]
        return parts
    if grammar is Grammar.CHANGE_NAME:
        assert record.change is not None
        return [record.change]
    if grammar is Grammar.OPTIONAL_CHANGE_NAME:
        return [record.change] if record.change else []
    if grammar is Grammar.PARTS:
        return [", ".join(record.parts)] if record.parts else []
    if grammar is Grammar.MOVE:
        assert record.change is not None
        return [record.change, *(["after", record.after] if record.after else ["first"])]
    return []


def _covers_words(record: Record) -> list[str]:
    return ["covers", _items(record.covers)] if record.covers else []


def render(record: Record) -> str:
    """A record's text, without the list marker in front of it."""
    spec = KINDS[record.kind]
    words = [record.date.isoformat(), f"({record.kind.value})", *_arguments(record)]
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


def _unknown_kind(word: str) -> ParseError:
    known = ", ".join(f"({k.value})" for k in RecordKind)
    return _fail(None, f'"({word})" is not a kind of record. The kinds are {known}.')


def _kind_first(text: str) -> str | ParseError | None:
    """A record's text with its kind before its date, the order the reader works in.

    None when the text doesn't start like a record; a ParseError for the older shape,
    with the kind first.
    """
    date_first = _DATE_FIRST.match(text)
    if date_first is not None:
        return f"({date_first.group(2)}) {date_first.group(1)}{date_first.group(3)}"
    start = _START.match(text)
    if start is None:
        return None
    try:
        kind = RecordKind(start.group(1))
    except ValueError:
        return _unknown_kind(start.group(1))
    return _fail(kind, "A record starts with its date, YYYY-MM-DD, then its kind.")


def parse(text: str) -> Record | ParseError | None:  # noqa: PLR0911 - one return per refusal
    """Read a record from a line's text, without its list marker.

    None when the text doesn't start like a record at all; a ParseError when it
    does but has the wrong shape or an unknown kind.
    """
    reordered = _kind_first(text.strip())
    if not isinstance(reordered, str):
        return reordered
    start = _START.match(reordered)
    assert start is not None
    before_text, colon, after_text = reordered.partition(_TEXT_SEPARATOR)
    text = " ".join(before_text.split()) + colon + after_text
    try:
        kind = RecordKind(start.group(1))
    except ValueError:
        return _unknown_kind(start.group(1))
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
    return _built(Record(kind, date, who=who, text=text_value), spec.grammar, words)


_NAMED = (Grammar.CHANGE_NAME, Grammar.OPTIONAL_CHANGE_NAME, Grammar.MOVE, Grammar.ITEM)
"""The grammars whose arguments name an item or a change."""


def _built(head: Record, grammar: Grammar, words: list[str]) -> Record | ParseError:
    """The record with the arguments its grammar reads from the words before ``by``."""
    kind = head.kind
    if grammar is Grammar.PARTS:
        parts = _parts_arguments(kind, words)
        return parts if isinstance(parts, ParseError) else replace(head, parts=parts)
    if grammar in _NAMED:
        named = _named_arguments(kind, grammar, words)
        if isinstance(named, ParseError):
            return named
        change, after, item = named
        return replace(head, change=change, after=after, item=item)
    found = _read_arguments(kind, grammar, words)
    if isinstance(found, ParseError):
        return found
    verdict, items, fingerprint, covers = found
    return replace(head, verdict=verdict, items=items, fingerprint=fingerprint, covers=covers)


def _named_arguments(
    kind: RecordKind, grammar: Grammar, words: list[str]
) -> tuple[str | None, str | None, str | None] | ParseError:
    """The change, the change it went after, and the item, for a record that names an item
    or a change on a milestone's roadmap."""
    if grammar is Grammar.ITEM:
        if len(words) > 1 or (words and not _ITEM_NUMBER.match(words[0])):
            return _fail(kind, "Only one item number such as 1.2 may follow the kind.")
        return None, None, words[0] if words else None
    if grammar is Grammar.OPTIONAL_CHANGE_NAME:
        if not words:
            return None, None, None
        grammar = Grammar.CHANGE_NAME
    place = _change_arguments(kind, grammar, words)
    if isinstance(place, ParseError):
        return place
    return place[0], place[1], None


PART = re.compile(r"^(?:\d+\.\d+|proposal|design|specs/[a-z0-9][a-z0-9-]*)$")
"""A part of a change a revision names: an item number, ``proposal``, ``design`` or
``specs/<area>``."""


def _parts_arguments(kind: RecordKind, words: list[str]) -> tuple[str, ...] | ParseError | None:
    """The parts a ``(revised)`` record names, separated by ``, ``; None when it names none."""
    if not words:
        return None
    parts: list[str] = []
    for at, word in enumerate(words):
        last = at == len(words) - 1
        name = word if last else word.removesuffix(",")
        if (not last and not word.endswith(",")) or not PART.match(name):
            return _fail(
                kind,
                'Name the parts as item numbers, "proposal", "design" or "specs/<area>", '
                'separated by ", ".',
            )
        parts.append(name)
    return tuple(parts)


def _split_who(body: str) -> tuple[list[str], str | None]:
    """The argument words, and who wrote the record: None when it doesn't say."""
    words = body.split()
    if "by" not in words:
        return words, None
    at = words.index("by")
    return words[:at], " ".join(words[at + 1 :])


_LISTED = re.compile(r"^(\d+\.\d+)([,;]?)$")


def _list_words(kind: RecordKind, words: list[str]) -> list[str] | ParseError:
    """The argument words with the separators of their item lists taken out.

    Items in a list are separated by ``, ``, and a list that ``covers`` follows ends
    with ``;``; any other separator is refused.
    """
    out: list[str] = []
    for at, word in enumerate(words):
        listed = _LISTED.match(word)
        if listed is None:
            out.append(word)
            continue
        following = words[at + 1] if at + 1 < len(words) else None
        next_is_item = following is not None and _LISTED.match(following) is not None
        wanted = "," if next_is_item else (";" if following == "covers" else "")
        if listed.group(2) != wanted:
            return _fail(
                kind,
                'Separate the items with ", ", and end a list that "covers" follows with ";".',
            )
        out.append(listed.group(1))
    return out


_Arguments = tuple[Verdict | None, tuple[str, ...] | None, str | None, tuple[str, ...] | None]


def _read_arguments(  # noqa: PLR0911 - one return per grammar
    kind: RecordKind, grammar: Grammar, words: list[str]
) -> _Arguments | ParseError:
    """The arguments before ``by``, read by the kind's grammar."""
    if grammar in (Grammar.VERDICT, Grammar.COVERS, Grammar.ACCEPTANCE):
        listed = _list_words(kind, words)
        if isinstance(listed, ParseError):
            return listed
        words = listed
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


FINDING_SHAPE = "[<severity>] `<place>`: <text>"
FINDING_ARGUMENT = "<critical|warning|suggestion>: <place>: <text>"

_FINDING = re.compile(r"^\[(critical|warning|suggestion)\]\s+`([^`]+)`:\s+(\S.*)$")
_FINDING_ARGUMENT_QUOTED = re.compile(r"^(critical|warning|suggestion): `([^`]+)`: (\S.*)$")
_FINDING_ARGUMENT = re.compile(r"^(critical|warning|suggestion): (\S.*?): (\S.*)$")


def render_finding(finding: Finding) -> str:
    """A finding's text, without the list marker in front of it."""
    if "`" in finding.place:
        raise RecordError("A finding's place can't hold a backtick.")
    return f"[{finding.severity.value}] `{finding.place}`: {finding.text}"


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


_WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]|\\\\")
"""A Windows absolute path: a drive and a slash, or a network share."""


def _split_place(place: str) -> tuple[str, str]:
    """A place's path, and what follows it from its first colon after any drive letter."""
    start = 2 if _WINDOWS_ABSOLUTE.match(place) else 0
    colon = place.find(":", start)
    return (place, "") if colon < 0 else (place[:colon], place[colon:])


def relative_place(place: str, roots: Sequence[tuple[str, PurePath]]) -> str | None:
    """A finding's place with its path relative to a root; None when it is absolute elsewhere.

    ``roots`` pairs a prefix with a folder: the project's top folder with no
    prefix, and in an atlas each code repo on this machine with its name. An
    absolute path inside a root is written relative to it, with forward slashes,
    after the prefix; what follows the path, such as ``:12``, is kept. A
    relative path gets forward slashes, and a place that isn't a path is kept.
    Windows and POSIX paths are each compared in their own form, on any platform.
    """
    path, rest = _split_place(place)
    windows = bool(_WINDOWS_ABSOLUTE.match(path))
    if not windows and not path.startswith("/"):
        # Only a single word reads as a path; prose such as "`re \d+` pattern" is kept.
        if path and not any(char.isspace() or char == "`" for char in path):
            path = path.replace("\\", "/")
        return path + rest
    flavor: type[PurePath] = PureWindowsPath if windows else PurePosixPath
    given = flavor((ntpath if windows else posixpath).normpath(path))
    for prefix, folder in roots:
        base = flavor(folder)
        if not base.is_absolute() or not given.is_relative_to(base):
            continue
        inside = given.relative_to(base).as_posix()
        joined = "/".join(part for part in (prefix, inside) if part and part != ".")
        return (joined or ".") + rest
    return None


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

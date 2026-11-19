"""The acceptance fingerprint: a digest of everything an acceptance covers.

It covers what the human approved:

- the proposal, apart from its outcome;
- the change's review level: its Review line, or the project default;
- every delta, and the design;
- each task item's definition (number, title, criteria, verification, repo
  and, when present, the build tag), but none of its evidence. Given the items
  an acceptance names, only those are covered, so an item added later leaves
  the fingerprint as it was, and a named item that is gone changes it;
- the living text of what the deltas modify or remove, so that another change
  archiving into the same requirement withdraws this acceptance.

Every part is hashed without its comments and in its standard layout
(``record/writing/layout.py``), so line endings don't count, two checkouts of one commit
agree, and neither fixing the layout nor editing a comment, such as a template's
examples, withdraws an acceptance.
"""

import hashlib
import re
from collections.abc import Callable, Mapping, Sequence

from waymark.record.artifacts.changes import Change
from waymark.record.artifacts.specs import Spec
from waymark.record.artifacts.tasks import Item
from waymark.record.terms import ReviewLevel
from waymark.record.writing.layout import standard_layout

FINGERPRINT_LENGTH = 16
_ABSENT = "\x00absent"
_COMMENT = re.compile(r"(`[^`\n]*`)|<!--.*?(?:-->|\Z)", re.DOTALL)
"""A comment, or an inline code span, which is kept so a ``<!--`` written in one isn't a comment."""
_GONE = "﷐"
"""Marks where a comment was removed: a noncharacter, so never in the text itself."""
_FENCE = re.compile(r"^[ \t]*(```|~~~)")


def _line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _without_comments(text: str) -> str:
    """The text with its HTML comments removed, outside fenced code.

    A line left blank by a removed comment goes, and runs of blank lines become one.
    Text without a comment is returned as it is.
    """
    if "<!--" not in text:
        return text
    kept: list[str] = []
    prose: list[str] = []
    fence: str | None = None

    def flush() -> None:
        stripped = (
            _COMMENT.sub(lambda match: match.group(1) or _GONE, "\n".join(prose)) if prose else ""
        )
        for line in stripped.split("\n") if prose else ():
            if _GONE in line and not line.replace(_GONE, "").strip():
                continue
            kept.append(line.replace(_GONE, "").rstrip() if _GONE in line else line)
        prose.clear()

    for line in text.split("\n"):
        match = _FENCE.match(line)
        if fence is None and match:
            flush()
            fence = match.group(1)
            kept.append(line)
        elif fence is not None:
            kept.append(line)
            if match and match.group(1) == fence:
                fence = None
        else:
            prose.append(line)
    flush()
    collapsed: list[str] = []
    for line in kept:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    return "\n".join(collapsed)


def _laid_out(text: str) -> str:
    return standard_layout(_without_comments(_line_endings(text)))[0]


def fingerprint_parts(
    change: Change,
    specs: Mapping[str, Spec],
    default_review: ReviewLevel,
    items: Sequence[str] | None = None,
) -> list[tuple[str, str]]:
    """The labeled pieces of text the fingerprint is made of, in a fixed order."""
    parts: list[tuple[str, str]] = []
    if change.proposal is not None:
        parts.append(("proposal", change.proposal.accepted_text()))
    parts.append(("review", change.review_level(default_review).value))
    if change.design is not None:
        parts.append(("design", change.design.doc.text))
    for domain in sorted(change.deltas):
        delta = change.deltas[domain]
        spec = specs.get(domain)
        parts.append((f"delta:{domain}", delta.doc.text))
        names = list(delta.based_on())
        for name in sorted(names):
            living = spec.requirement(name) if spec else None
            text = "\n".join(living.block) if living else _ABSENT
            parts.append((f"base:{domain}:{' '.join(name.split()).casefold()}", text))
        if delta.purpose is not None:
            parts.append((f"base-purpose:{domain}", spec.purpose if spec else _ABSENT))
        if delta.repos is not None:
            parts.append((f"base-repos:{domain}", ", ".join(spec.repos) if spec else _ABSENT))
    if items is not None:
        parts.extend(_named_items(change, items))
    else:
        parts.extend(
            (f"item:{item.number}", _definition(item))
            for item in (change.tasks.items if change.tasks else ())
        )
    return parts


def _definition(item: Item) -> str:
    definition = [
        item.title,
        item.criteria if item.criteria is not None else _ABSENT,
        item.verify if item.verify is not None else _ABSENT,
        item.repo if item.repo is not None else _ABSENT,
    ]
    if item.build is not None:
        definition.append(item.build)
    return "\x00".join(definition)


def _named_items(change: Change, items: Sequence[str]) -> list[tuple[str, str]]:
    """The parts of the items an acceptance names; a named item that is gone is absent."""
    tasks = change.tasks
    parts: list[tuple[str, str]] = []
    for number in items:
        item = tasks.item(number) if tasks else None
        parts.append((f"item:{number}", _definition(item) if item else _ABSENT))
    return parts


def change_fingerprint(
    change: Change,
    specs: Mapping[str, Spec],
    default_review: ReviewLevel,
    items: Sequence[str] | None = None,
) -> str:
    """The fingerprint of a change as it now stands, over the given items or every item."""
    return _digest(fingerprint_parts(change, specs, default_review, items), _laid_out)


def _digest(parts: Sequence[tuple[str, str]], normalize: Callable[[str], str]) -> str:
    digest = hashlib.sha256()
    for label, text in parts:
        data = normalize(text).encode("utf-8")
        digest.update(f"{label}\x00{len(data)}\x00".encode())
        digest.update(data)
    return digest.hexdigest()[:FINGERPRINT_LENGTH]

"""The record's label lines: their names, how they are written and how they are read.

A label line is ``- **<Name>:** <value>``: the name in bold with the colon inside.
Only that form is read as the label. A label written plain (``- <Name>: <value>``)
or bold with the colon outside (``- **<Name>**: <value>``) is matched too, so that
``wm check`` can report it and ``wm check --fix`` can make it bold.
"""

import enum
import re
from dataclasses import dataclass

from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import Document

# A proposal's facts.
OWNER = "Owner"
MILESTONE = "Milestone"
AFTER = "After"
PATH = "Path"
REVIEW = "Review"
# A proposal's Impact and Outcome.
SPECS = "Specs"
USER_VISIBLE = "User-visible"
CODE = "Code"
BUILT = "Built"
DIFFERS = "Differs"
# A task item's lines.
BUILD = "Build"
REPO = "Repo"
CRITERIA = "Criteria"
VERIFY = "Verify"
# A decision's parts.
STATUS = "Status"
DECIDED_BY = "Decided by"
OPTIONS = "Options"
CHOICE = "Choice"
WHY = "Why"
# A delta's renames and removals, and the Repos line of specs and deltas.
FROM = "From"
TO = "To"
REASON = "Reason"
REPOS = "Repos"
# A resource's lines.
KIND = "Kind"
SERVES = "Serves"
VERIFIED = "Verified"

KNOWN = frozenset(
    {
        OWNER,
        MILESTONE,
        AFTER,
        PATH,
        REVIEW,
        SPECS,
        USER_VISIBLE,
        CODE,
        BUILT,
        DIFFERS,
        BUILD,
        REPO,
        CRITERIA,
        VERIFY,
        STATUS,
        DECIDED_BY,
        OPTIONS,
        CHOICE,
        WHY,
        FROM,
        TO,
        REASON,
        REPOS,
        KIND,
        SERVES,
        VERIFIED,
    }
)
"""Every label the record reads."""
BARE = frozenset({REASON, REPOS})
"""The labels written without a list bullet, at the start of a line."""
ITEM_ORDER = (BUILD, REPO, CRITERIA, VERIFY)
"""The order of a task item's label lines."""

_NAME = r"[A-Z][A-Za-z-]*(?: [a-z][A-Za-z-]*)*"

LABEL = re.compile(
    r"^(?P<bullet>[-*][ \t]+)?"
    rf"(?:\*\*(?P<bold>{_NAME}):\*\*|\*\*(?P<outside>{_NAME})\*\*:|(?P<plain>{_NAME}):)"
    r"(?:[ \t]+(?P<value>.*?))?[ \t]*$"
)
"""A label line, with or without a list bullet, in any of the three forms."""


class LabelForm(enum.Enum):
    """How a label was written."""

    BOLD = "bold"
    """``**Name:**``, the form the record uses."""
    PLAIN = "plain"
    """``Name:``, without bold."""
    COLON_OUTSIDE = "colon-outside"
    """``**Name**:``, bold with the colon outside."""


@dataclass(frozen=True)
class Label:
    """A label line as read: its name, value, form and whether it had a bullet."""

    name: str
    value: str
    form: LabelForm
    bullet: bool


def read_label(text: str) -> Label | None:
    """Read a label line in the bold form; None when the text is not one.

    The text is matched as given: strip its indentation first when it may have some.
    """
    label = match_label(text)
    return label if label is not None and label.form is LabelForm.BOLD else None


def match_label(text: str) -> Label | None:
    """Match a label line in any of the three forms; None when the text is not one."""
    match = LABEL.match(text)
    if match is None:
        return None
    for group, form in (
        ("bold", LabelForm.BOLD),
        ("outside", LabelForm.COLON_OUTSIDE),
        ("plain", LabelForm.PLAIN),
    ):
        if match.group(group) is not None:
            return Label(
                match.group(group),
                (match.group("value") or "").strip(),
                form,
                match.group("bullet") is not None,
            )
    return None  # pragma: no cover - one of the groups always matches


def label_line(name: str, value: str = "", *, bullet: bool = True) -> str:
    """Write a label line in the bold form: ``- **<name>:** <value>``."""
    line = f"**{name}:**"
    if value:
        line = f"{line} {value}"
    return f"- {line}" if bullet else line


def plain_label(text: str) -> Label | None:
    """A known label on a line, written plain or with the colon outside the bold.

    A label counts with a bullet at any indentation, or without one at the start of
    the line for the labels written bare, such as ``Repos:``. None otherwise.
    """
    body = text.lstrip(" ")
    label = match_label(body)
    if label is None or label.form is LabelForm.BOLD or label.name not in KNOWN:
        return None
    if not label.bullet and (body != text or label.name not in BARE):
        return None
    return label


def plain_label_problems(doc: Document) -> list[Problem]:
    """A problem for each known label written plain or with the colon outside the bold,
    outside fenced code and comments."""
    problems: list[Problem] = []
    in_comment = False
    for index, line in enumerate(doc.lines):
        if line.in_fence:
            continue
        if in_comment or "<!--" in line.text:
            after = line.text[line.text.find("<!--") :] if "<!--" in line.text else line.text
            in_comment = "-->" not in after
            continue
        label = plain_label(line.text)
        if label is None:
            continue
        wanted = label_line(label.name, bullet=label.bullet)
        problems.append(
            Problem(
                doc.path,
                index + 1,
                "plain-label",
                f'A label is written in bold with the colon inside: "{wanted}". Fix the line, '
                'or run "wm check --fix".',
            )
        )
    return problems

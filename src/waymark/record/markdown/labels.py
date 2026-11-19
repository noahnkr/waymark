"""The record's label lines: their names, how they are written and how they are read.

A label line is ``- **<Name>:** <value>``: the name in bold with the colon inside.
While the record moves to that form, a line is also read with the label written
plain (``- <Name>: <value>``) or bold with the colon outside
(``- **<Name>**: <value>``), and the match says which form it was in.
"""

import enum
import re
from dataclasses import dataclass

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
    """Read a label line; None when the text is not one.

    The text is matched as given: strip its indentation first when it may have some.
    """
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

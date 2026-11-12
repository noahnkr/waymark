"""Names of changes, specs, milestones and explorations, and of archived folders."""

import datetime
import re
from dataclasses import dataclass

_NAME = re.compile(r"[a-z]+(?:-[a-z]+)*")
_ARCHIVE_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})-(.+)")

NAME_RULE = "lowercase words joined by hyphens, with no digits"


def is_valid_name(name: str) -> bool:
    """Whether a name is kebab-case with no digits."""
    return _NAME.fullmatch(name) is not None


@dataclass(frozen=True, order=True)
class ArchiveName:
    """An archived folder's name: the date it was archived, then the original name."""

    date: datetime.date
    name: str

    @property
    def folder(self) -> str:
        return f"{self.date.isoformat()}-{self.name}"


def parse_archive_name(folder: str) -> ArchiveName | None:
    """Read ``YYYY-MM-DD-<name>``; None when the folder name doesn't follow it."""
    match = _ARCHIVE_NAME.fullmatch(folder)
    if match is None or not is_valid_name(match.group(2)):
        return None
    try:
        date = datetime.date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return ArchiveName(date, match.group(2))

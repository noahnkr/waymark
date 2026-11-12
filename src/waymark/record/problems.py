"""Problems found while reading the record."""

from dataclasses import dataclass

WHOLE_FILE = 0
"""The line number of a problem that concerns a whole file or folder."""


@dataclass(frozen=True, order=True)
class Problem:
    """One thing wrong in the record: where it is, what it is, and how to fix it.

    ``path`` is relative to the record's root and uses forward slashes, so the
    same files give the same problems on every platform. ``line`` is 1-based.
    """

    path: str
    line: int
    code: str
    message: str

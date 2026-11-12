"""Reading the record's files and folders.

Files are read as UTF-8 and kept exactly as they are on disk, line endings
included. Paths handed in and out are relative to the record's root and use
forward slashes.
"""

from dataclasses import dataclass
from pathlib import Path

from waymark.record.problems import WHOLE_FILE, Problem
from waymark.record.text import Document


@dataclass(frozen=True)
class Entry:
    """A file or folder inside a record folder."""

    name: str
    is_dir: bool


class RecordFiles:
    """The files under one record root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, relative: str) -> Path:
        return self.root.joinpath(*relative.split("/")) if relative else self.root

    def is_file(self, relative: str) -> bool:
        return self.path(relative).is_file()

    def entries(self, relative: str) -> tuple[Entry, ...]:
        """A folder's files and folders, sorted by name; hidden entries are left out."""
        folder = self.path(relative)
        if not folder.is_dir():
            return ()
        found = [
            Entry(child.name, child.is_dir())
            for child in folder.iterdir()
            if not child.name.startswith(".")
        ]
        return tuple(sorted(found, key=lambda entry: entry.name))

    def read(self, relative: str, problems: list[Problem]) -> str | None:
        """A file's text; a file that can't be read as UTF-8 is reported as a problem."""
        try:
            return self.path(relative).read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "not-utf8",
                    "The file is not valid UTF-8. Save it again as UTF-8.",
                )
            )
        except OSError as error:
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unreadable",
                    f"The file can't be read ({error.strerror or error}). Check that it exists "
                    "and that you may read it.",
                )
            )
        return None

    def document(self, relative: str, problems: list[Problem]) -> Document | None:
        """A file parsed as markdown, or None when it can't be read."""
        text = self.read(relative, problems)
        return None if text is None else Document.parse(relative, text)

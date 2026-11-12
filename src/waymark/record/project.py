"""Finding the project: the folder that holds the record."""

from dataclasses import dataclass
from pathlib import Path

from waymark.record.config import CONFIG_FILE

RECORD_DIR = "waymark"


class ProjectNotFoundError(Exception):
    """No record was found at or above the starting folder."""

    def __init__(self, start: Path) -> None:
        super().__init__(
            f'No Waymark project found at or above "{start}". '
            f'A project has a "{RECORD_DIR}/{CONFIG_FILE}" file at its top. '
            "Change to the project's folder, or initialize one."
        )
        self.start = start


@dataclass(frozen=True)
class Project:
    """A project: the repository, or the atlas, whose top folder holds the record."""

    root: Path

    @property
    def record_root(self) -> Path:
        return self.root / RECORD_DIR


def find_project(start: Path) -> Project:
    """Find the project that contains a folder, looking upward from it.

    The record sits in the same place in a repository and in an atlas, so both
    are found the same way; the settings say which one it is.
    """
    origin = start.resolve()
    for folder in (origin, *origin.parents):
        if (folder / RECORD_DIR / CONFIG_FILE).is_file():
            return Project(folder)
    raise ProjectNotFoundError(start)

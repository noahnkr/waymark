"""Writing the record: several files and a folder move as one step.

A transaction collects the files to write and the folder to move, then applies
them together. If anything fails, every file is put back and the move undone,
so a multi-file operation either completes or leaves the record as it was.
"""

from pathlib import Path

from waymark.record.files import RecordFiles


class StoreError(Exception):
    """The record could not be written; it has been left as it was."""


class Transaction:
    """Staged writes under one record root. Paths are record-relative, with forward slashes."""

    def __init__(self, files: RecordFiles) -> None:
        self._files = files
        self._writes: dict[str, str] = {}
        self._moves: list[tuple[str, str]] = []

    def write(self, relative: str, text: str) -> None:
        """Stage a file's new text. Files are written as UTF-8, exactly as given."""
        self._writes[relative] = text

    def move(self, source: str, target: str) -> None:
        """Stage a folder move. It happens after the writes, which use the old paths."""
        self._moves.append((source, target))

    def staged(self, relative: str) -> str | None:
        """The text staged for a file, if any."""
        return self._writes.get(relative)

    @property
    def paths(self) -> tuple[str, ...]:
        """Every file staged for writing, in order."""
        return tuple(sorted(self._writes))

    def commit(self) -> None:
        """Apply everything, or nothing."""
        originals: dict[Path, bytes | None] = {}
        moved: list[tuple[Path, Path]] = []
        try:
            for relative, text in sorted(self._writes.items()):
                path = self._files.path(relative)
                if path not in originals:
                    originals[path] = path.read_bytes() if path.is_file() else None
                path.parent.mkdir(parents=True, exist_ok=True)
                _replace(path, text.encode("utf-8"))
            for source, target in self._moves:
                origin, destination = self._files.path(source), self._files.path(target)
                if destination.exists():
                    raise FileExistsError(f"{target} already exists")
                destination.parent.mkdir(parents=True, exist_ok=True)
                origin.rename(destination)
                moved.append((origin, destination))
        except OSError as error:
            _roll_back(originals, moved)
            raise StoreError(
                f"The record could not be written ({error}). Nothing was changed. "
                "Check the folder's permissions and that no other program has the files open."
            ) from error


def _replace(path: Path, data: bytes) -> None:
    """Write a file through a temporary neighbor, so a crash never leaves it half written."""
    temporary = path.with_name(f"{path.name}.wm-tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def _roll_back(originals: dict[Path, bytes | None], moved: list[tuple[Path, Path]]) -> None:
    for origin, destination in reversed(moved):
        try:
            destination.rename(origin)
        except OSError:
            continue
    for path, data in originals.items():
        try:
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        except OSError:
            continue

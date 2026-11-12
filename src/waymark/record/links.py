"""Links between record files: resolving them and checking that they lead somewhere."""

import posixpath
import re
from pathlib import Path
from urllib.parse import unquote

from waymark.record.problems import Problem
from waymark.record.text import Document

_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def is_absolute(target: str) -> bool:
    """Whether a link names an absolute file path, which breaks on another machine."""
    return (target.startswith("/") and not target.startswith("//")) or bool(_DRIVE.match(target))


def local_path(target: str) -> str | None:
    """The relative file path a link points at.

    None for links wm doesn't follow: web addresses, absolute paths and anchors
    within the same file.
    """
    if is_absolute(target) or _SCHEME.match(target) or target.startswith("//"):
        return None
    path = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(path) or None


def resolve(doc_path: str, target: str) -> str | None:
    """Where a link in a document leads, relative to the record's root.

    The result starts with ``../`` when the link leaves the record.
    """
    path = local_path(target)
    if path is None:
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(doc_path), path))


class LinkChecker:
    """Checks that links lead to existing files, matching names exactly.

    Names are compared case-sensitively on every platform, so a link that works
    on one machine works on all of them. Folder listings are remembered for the
    life of the checker, which is one command.
    """

    def __init__(self, record_root: Path) -> None:
        self._root = record_root
        self._listings: dict[Path, frozenset[str]] = {}

    def _names(self, folder: Path) -> frozenset[str]:
        if folder not in self._listings:
            try:
                names = frozenset(child.name for child in folder.iterdir())
            except OSError:
                names = frozenset()
            self._listings[folder] = names
        return self._listings[folder]

    def exists(self, relative: str) -> bool:
        """Whether a path relative to the record's root exists, with exact names."""
        current = self._root
        for part in relative.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                current = current.parent
                continue
            if part not in self._names(current):
                return False
            current = current / part
        return True

    def problems(self, doc: Document) -> list[Problem]:
        """The links in a document that are broken or not portable."""
        found: list[Problem] = []
        for link in doc.links():
            target = link.target
            if is_absolute(target):
                message = (
                    f'"{target}" is an absolute path, which only works on one machine. '
                    "Write it relative to this file."
                )
                found.append(Problem(doc.path, link.index + 1, "absolute-link", message))
                continue
            path = local_path(target)
            if path is None:
                continue
            if "\\" in path:
                message = f'"{target}" uses backslashes. Write the link with forward slashes.'
                found.append(Problem(doc.path, link.index + 1, "broken-link", message))
                continue
            resolved = resolve(doc.path, target)
            if resolved is None or not self.exists(resolved):
                message = (
                    f'"{target}" doesn\'t lead to a file or folder. Fix the path (names are '
                    "matched exactly, including case), or remove the link."
                )
                found.append(Problem(doc.path, link.index + 1, "broken-link", message))
        return found

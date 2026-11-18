"""Branches: each active change's branch, the branch it is based on, and what it comes after.

A change's branch is its name. Its base is the branch of the change it comes after, until
that change has merged; then the default branch. A change is archived on its own branch
before its pull request, so it has merged once the default branch holds its archived
folder, however it was merged. Git is asked in the record's own repository, once for the
default branch and once for the changes archived on it, and only when a change comes after
another.
"""

from dataclasses import dataclass
from pathlib import Path

from waymark.record.artifacts.changes import Change
from waymark.record.machine import git
from waymark.record.names import parse_archive_name
from waymark.record.record import ARCHIVE, CHANGES, Record


@dataclass(frozen=True)
class ChangeBranch:
    """Where a change's work lives: its branch, its base, and the change it comes after.

    ``merged`` is true when the change it comes after is archived in this record, or the
    default branch holds its archived folder; the base is then the default branch.
    """

    branch: str
    base: str
    after: str | None
    merged: bool


class Branches:
    """Branches and bases for a record's active changes, with git asked once per question."""

    def __init__(self, record: Record) -> None:
        self._record = record
        self._root = git.repository_root(record.project.root)
        self._default: str | None = None
        self._merged_names: frozenset[str] | None = None
        self._archived = {entry.name for entry in record.archived_changes}

    @property
    def default(self) -> str:
        """The default branch: the ``origin`` remote's HEAD, or ``main``."""
        if self._default is None:
            root = self._root
            self._default = git.default_branch(root) if root else git.DEFAULT_BRANCH
        return self._default

    def _archive_folder(self, root: Path) -> str | None:
        """The record's ``changes/archive`` folder, relative to the repository's top."""
        try:
            relative = self._record.project.record_root.resolve().relative_to(root.resolve())
        except ValueError:
            return None
        return "/".join((*relative.parts, CHANGES, ARCHIVE))

    def _names_on_default(self) -> frozenset[str]:
        """The names of the changes archived on the default branch."""
        if self._merged_names is None:
            root = self._root
            folder = self._archive_folder(root) if root is not None else None
            folders = git.archived_on(root, self.default, folder) if root and folder else ()
            parsed = (parse_archive_name(name) for name in folders)
            self._merged_names = frozenset(entry.name for entry in parsed if entry is not None)
        return self._merged_names

    def _is_merged(self, change: str) -> bool:
        if change in self._archived and change not in self._record.changes:
            return True
        return change in self._names_on_default()

    def of(self, change: Change) -> ChangeBranch:
        """The branch and base of a change."""
        after = change.proposal.after if change.proposal else None
        if after is None or after == change.name:
            return ChangeBranch(change.name, self.default, after, merged=False)
        merged = self._is_merged(after)
        active = after in self._record.changes
        base = after if active and not merged else self.default
        return ChangeBranch(change.name, base, after, merged=merged)

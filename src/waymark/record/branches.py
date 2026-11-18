"""Branches: each active change's branch, the branch it is based on, and what it comes after.

A change's branch is its name. Its base is the branch of the change it comes after, while
that change is active and its branch isn't merged into the default branch; otherwise the
default branch. Git is asked in the record's own repository, once for the default branch
and once for each change another comes after.
"""

from dataclasses import dataclass

from waymark.record import git
from waymark.record.changes import Change
from waymark.record.record import Record


@dataclass(frozen=True)
class ChangeBranch:
    """Where a change's work lives: its branch, its base, and the change it comes after.

    ``merged`` is true when the change it comes after is archived, or its branch is
    already in the default branch; the base is then the default branch.
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
        self._merged: dict[str, bool] = {}
        self._archived = {entry.name for entry in record.archived_changes}

    @property
    def default(self) -> str:
        """The default branch: the ``origin`` remote's HEAD, or ``main``."""
        if self._default is None:
            root = self._root
            self._default = git.default_branch(root) if root else git.DEFAULT_BRANCH
        return self._default

    def _is_merged(self, change: str) -> bool:
        if change in self._archived and change not in self._record.changes:
            return True
        if change not in self._merged:
            root = self._root
            self._merged[change] = (
                git.is_merged(root, change, self.default) if root is not None else False
            )
        return self._merged[change]

    def of(self, change: Change) -> ChangeBranch:
        """The branch and base of an active change."""
        after = change.proposal.after if change.proposal else None
        if after is None or after == change.name:
            return ChangeBranch(change.name, self.default, after, merged=False)
        merged = self._is_merged(after)
        active = after in self._record.changes
        base = after if active and not merged else self.default
        return ChangeBranch(change.name, base, after, merged=merged)

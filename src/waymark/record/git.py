"""What the record model asks git: where the repository is, and when things last changed.

Only local, read-only git commands are run. Nothing here clones, pulls, pushes
or touches the network.
"""

import datetime
import subprocess
from collections.abc import Iterable
from pathlib import Path


class GitError(Exception):
    """Git is missing, or a git command failed."""


def _run(folder: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(folder), "-c", "core.quotepath=off", *arguments],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise GitError(
            "git could not be run. Waymark needs git; install it and make sure it is on PATH."
        ) from error
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise GitError(f"git {arguments[0]} failed: {detail}")
    return result.stdout


def repository_root(folder: Path) -> Path | None:
    """The top folder of the git repository that contains a folder; None outside one."""
    try:
        return Path(_run(folder, "rev-parse", "--show-toplevel").strip())
    except GitError:
        return None


def user_name(folder: Path) -> str | None:
    """The name git signs commits with here; None when it isn't set."""
    try:
        return _run(folder, "config", "user.name").strip() or None
    except GitError:
        return None


def current_branch(folder: Path) -> str | None:
    """The checked-out branch; None when HEAD is detached or this is not a repository."""
    try:
        return _run(folder, "branch", "--show-current").strip() or None
    except GitError:
        return None


def last_changed(repository: Path, folders: Iterable[str]) -> dict[str, datetime.datetime]:
    """When each folder last changed in git's history.

    Folders are given relative to the repository root, with forward slashes. A
    folder with no commits yet is left out. One pass over the history answers
    for every folder.
    """
    wanted = {folder.strip("/") for folder in folders}
    found: dict[str, datetime.datetime] = {}
    if not wanted:
        return found
    try:
        log = _run(repository, "log", "--format=@%cI", "--name-only", "--", *sorted(wanted))
    except GitError:
        return found
    when: datetime.datetime | None = None
    for line in log.splitlines():
        if line.startswith("@"):
            when = datetime.datetime.fromisoformat(line[1:])
        elif line and when is not None:
            for folder in wanted - found.keys():
                if line == folder or line.startswith(f"{folder}/"):
                    found[folder] = when
            if len(found) == len(wanted):
                break
    return found

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


def version() -> str | None:
    """The installed git's version line; None when git can't be run."""
    try:
        return _run(Path.cwd(), "--version").strip() or None
    except GitError:
        return None


def is_ignored(repository: Path, relative: str) -> bool:
    """Whether git ignores a path in a repository (relative to its top, with forward slashes)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "check-ignore", "-q", "--no-index", "--", relative],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def exclude(repository: Path, relative: str) -> None:
    """Keep a path out of this clone's commits, through its own exclude file.

    The exclude file belongs to the clone and is never committed, so nothing
    the project shares changes.
    """
    where = Path(_run(repository, "rev-parse", "--git-path", "info/exclude").strip())
    path = where if where.is_absolute() else repository / where
    current = path.read_bytes().decode("utf-8", errors="replace") if path.is_file() else ""
    separator = "" if not current or current.endswith("\n") else "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{separator}/{relative}\n")


def config_value(repository: Path, key: str) -> str | None:
    """A setting from this clone's own git config; None when it isn't set there."""
    try:
        return _run(repository, "config", "--local", "--get", key).strip() or None
    except GitError:
        return None


def set_config(repository: Path, key: str, value: str) -> None:
    """Set a setting in this clone's own git config. Nothing shared changes."""
    _run(repository, "config", "--local", key, value)


def default_hooks_folder(repository: Path) -> Path:
    """The folder git reads hooks from when ``core.hooksPath`` is not set."""
    common = Path(_run(repository, "rev-parse", "--git-common-dir").strip())
    return (common if common.is_absolute() else repository / common) / "hooks"


def staged_paths(repository: Path) -> tuple[str, ...]:
    """The paths the next commit changes, relative to the repository's top."""
    try:
        listing = _run(repository, "diff", "--cached", "--name-only", "-z")
    except GitError:
        return ()
    return tuple(path for path in listing.split("\0") if path)


def stage(repository: Path, paths: Iterable[str]) -> None:
    """Stage files for the next commit."""
    _run(repository, "add", "--", *paths)


def stage_executable(repository: Path, paths: Iterable[str]) -> None:
    """Stage files with their executable bit, which a checkout on Windows can't set itself."""
    _run(repository, "add", "--chmod=+x", "--", *paths)


def remote_url(repository: Path, remote: str = "origin") -> str | None:
    """A remote's URL as this clone's config has it; nothing is fetched."""
    try:
        return _run(repository, "remote", "get-url", remote).strip() or None
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

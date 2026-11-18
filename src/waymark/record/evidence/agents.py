"""The hooks' marker per agent: whether its ending was recorded from a handback.

A marker is a small file at ``<git dir>/waymark/agents/<agent_id>`` holding
``recorded`` or ``attempts: <n>``. It belongs to the clone (to the working
tree, in a linked worktree), is never committed and is read by no view: it is
state the hooks pass from an agent's handback to its stop, not a copy of the
record.

An ``agent_id`` that isn't letters, digits, ``-`` or ``_`` is ignored, so a
payload can't name a path. Outside a git repository nothing is read or written.
Writing a marker removes markers older than a day.
"""

import re
import time
from dataclasses import dataclass
from pathlib import Path

from waymark.record.machine import git

AGENTS_DIR = "waymark/agents"
"""Where the markers live, inside the git folder."""
MAX_AGE_SECONDS = 24 * 60 * 60
"""How old a marker gets before writing another one removes it."""

_RECORDED = "recorded"
_ATTEMPTS = re.compile(r"attempts: (\d+)")
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class Marker:
    """What the hooks know about one agent's handback."""

    recorded: bool
    attempts: int


def _is_safe(agent_id: str) -> bool:
    return _SAFE_ID.fullmatch(agent_id) is not None


def _folder(where: Path) -> Path | None:
    try:
        return git.git_path(where, AGENTS_DIR)
    except git.GitError:
        return None


def _marker_path(where: Path, agent_id: str) -> Path | None:
    if not _is_safe(agent_id):
        return None
    folder = _folder(where)
    return None if folder is None else folder / agent_id


def _sweep(folder: Path) -> None:
    oldest = time.time() - MAX_AGE_SECONDS
    try:
        children = list(folder.iterdir())
    except OSError:
        return
    for child in children:
        try:
            if child.is_file() and child.stat().st_mtime < oldest:
                child.unlink()
        except OSError:
            continue


def _read(path: Path) -> Marker | None:
    try:
        text = path.read_bytes().decode("utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if text == _RECORDED:
        return Marker(recorded=True, attempts=0)
    found = _ATTEMPTS.fullmatch(text)
    if found is None:
        return None
    return Marker(recorded=False, attempts=int(found.group(1)))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _sweep(path.parent)
    path.write_text(f"{text}\n", encoding="utf-8", newline="")


def read_marker(where: Path, agent_id: str) -> Marker | None:
    """An agent's marker; None when it has none, or the id or the file is not usable."""
    path = _marker_path(where, agent_id)
    return None if path is None else _read(path)


def mark_recorded(where: Path, agent_id: str) -> None:
    """Note that an agent's ending was recorded from its handback."""
    path = _marker_path(where, agent_id)
    if path is not None:
        _write(path, _RECORDED)


def count_attempt(where: Path, agent_id: str) -> int:
    """Count one more refused handback for an agent, and give the new count.

    An unusable id, or a folder outside a repository, counts nothing and gives 0.
    """
    path = _marker_path(where, agent_id)
    if path is None:
        return 0
    marker = _read(path)
    attempts = (marker.attempts if marker is not None and not marker.recorded else 0) + 1
    _write(path, f"attempts: {attempts}")
    return attempts


def remove_marker(where: Path, agent_id: str) -> None:
    """Remove an agent's marker, if it has one."""
    path = _marker_path(where, agent_id)
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return

"""The hooks' marker per agent, kept in the clone's git folder."""

import os
import subprocess
import time
from pathlib import Path

import pytest

from tests.conftest import git_init
from waymark.record.evidence.agents import (
    MAX_AGE_SECONDS,
    Marker,
    count_attempt,
    mark_recorded,
    read_marker,
    remove_marker,
)


def files_under(folder: Path) -> set[Path]:
    return {path for path in folder.rglob("*") if path.is_file()}


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    git_init(root)
    return root


def test_marker_is_kept_in_the_git_folder(repository: Path) -> None:
    before = files_under(repository)
    mark_recorded(repository, "agent-1_a")
    assert read_marker(repository, "agent-1_a") == Marker(recorded=True, attempts=0)
    path = repository / ".git" / "waymark" / "agents" / "agent-1_a"
    assert path.read_text(encoding="utf-8") == "recorded\n"
    assert files_under(repository) - before == {path}


def test_agent_without_a_marker_has_none(repository: Path) -> None:
    assert read_marker(repository, "agent-1") is None


def test_refused_attempts_are_counted(repository: Path) -> None:
    assert count_attempt(repository, "agent-1") == 1
    assert read_marker(repository, "agent-1") == Marker(recorded=False, attempts=1)
    assert count_attempt(repository, "agent-1") == 2
    path = repository / ".git" / "waymark" / "agents" / "agent-1"
    assert path.read_text(encoding="utf-8") == "attempts: 2\n"
    assert read_marker(repository, "agent-2") is None


def test_recorded_after_attempts_replaces_the_count(repository: Path) -> None:
    count_attempt(repository, "agent-1")
    mark_recorded(repository, "agent-1")
    assert read_marker(repository, "agent-1") == Marker(recorded=True, attempts=0)


def test_marker_is_removed(repository: Path) -> None:
    mark_recorded(repository, "agent-1")
    remove_marker(repository, "agent-1")
    assert read_marker(repository, "agent-1") is None
    remove_marker(repository, "agent-1")


def test_marker_is_read_from_a_folder_inside_the_repository(repository: Path) -> None:
    nested = repository / "src" / "app"
    nested.mkdir(parents=True)
    mark_recorded(nested, "agent-1")
    assert read_marker(repository, "agent-1") == Marker(recorded=True, attempts=0)
    assert (repository / ".git" / "waymark" / "agents" / "agent-1").is_file()


@pytest.mark.parametrize(
    "agent_id", ["", "../escape", "a/b", "a\\b", "..", ".", "a b", "a.b", "C:x", "agent\n"]
)
def test_unsafe_agent_id_is_ignored(repository: Path, agent_id: str) -> None:
    before = files_under(repository)
    mark_recorded(repository, agent_id)
    assert count_attempt(repository, agent_id) == 0
    assert read_marker(repository, agent_id) is None
    remove_marker(repository, agent_id)
    assert files_under(repository) == before
    assert not (repository / ".git" / "waymark").exists()
    assert not (repository.parent / "escape").exists()


def test_old_markers_are_swept_when_one_is_written(repository: Path) -> None:
    mark_recorded(repository, "old")
    mark_recorded(repository, "recent")
    folder = repository / ".git" / "waymark" / "agents"
    stale = time.time() - MAX_AGE_SECONDS - 60
    os.utime(folder / "old", (stale, stale))
    assert read_marker(repository, "old") is not None
    count_attempt(repository, "new")
    assert read_marker(repository, "old") is None
    assert read_marker(repository, "recent") == Marker(recorded=True, attempts=0)
    assert read_marker(repository, "new") == Marker(recorded=False, attempts=1)


def test_unreadable_marker_counts_as_none(repository: Path) -> None:
    mark_recorded(repository, "agent-1")
    path = repository / ".git" / "waymark" / "agents" / "agent-1"
    path.write_text("something else\n", encoding="utf-8")
    assert read_marker(repository, "agent-1") is None
    assert count_attempt(repository, "agent-1") == 1


def test_outside_a_repository_nothing_is_written(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    mark_recorded(plain, "agent-1")
    assert count_attempt(plain, "agent-1") == 0
    assert read_marker(plain, "agent-1") is None
    remove_marker(plain, "agent-1")
    assert files_under(tmp_path) == set()


def test_worktree_keeps_its_markers_in_its_own_git_folder(repository: Path) -> None:
    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout

    git(
        "-c",
        "user.email=sam@example.com",
        "commit",
        "--quiet",
        "--allow-empty",
        "--message",
        "chore: start",
    )
    worktree = repository.parent / "linked"
    git("worktree", "add", "--quiet", str(worktree))
    assert (worktree / ".git").is_file()

    mark_recorded(worktree, "agent-1")
    assert read_marker(worktree, "agent-1") == Marker(recorded=True, attempts=0)
    assert read_marker(repository, "agent-1") is None
    assert not (worktree / "waymark").exists()
    found = list((repository / ".git" / "worktrees").rglob("agent-1"))
    assert len(found) == 1
    assert found[0].parent.name == "agents"
    assert files_under(worktree) == {worktree / ".git"}

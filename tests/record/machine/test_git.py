"""What the record model asks git."""

import datetime
import os
import subprocess
from pathlib import Path

import pytest

from waymark.record.machine.git import (
    current_branch,
    head_commit,
    last_changed,
    repository_root,
    tracked,
)


def git(folder: Path, *arguments: str, date: str | None = None) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Sam Doe",
        "GIT_AUTHOR_EMAIL": "sam@example.com",
        "GIT_COMMITTER_NAME": "Sam Doe",
        "GIT_COMMITTER_EMAIL": "sam@example.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    if date:
        environment["GIT_AUTHOR_DATE"] = environment["GIT_COMMITTER_DATE"] = date
    subprocess.run(
        ["git", "-C", str(folder), *arguments], check=True, capture_output=True, env=environment
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--quiet", "--initial-branch=trunk")
    return root


def commit(repository: Path, relative: str, date: str) -> None:
    target = repository / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{date}\n", encoding="utf-8")
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "--message", "chore: change a file", date=date)


def test_repository_root_is_found_from_a_folder_inside_it(repository: Path) -> None:
    nested = repository / "waymark" / "changes"
    nested.mkdir(parents=True)
    found = repository_root(nested)
    assert found is not None
    assert found.resolve() == repository.resolve()


def test_folder_outside_a_repository_has_no_root(tmp_path: Path) -> None:
    outside = tmp_path / "plain"
    outside.mkdir()
    git(outside, "init", "--quiet")
    assert repository_root(outside) is not None
    assert repository_root(tmp_path / "missing") is None


def test_current_branch_is_read_from_git(repository: Path) -> None:
    assert current_branch(repository) == "trunk"
    commit(repository, "a.txt", "2026-01-10T09:00:00+00:00")
    git(repository, "switch", "--quiet", "--create", "add-limit")
    assert current_branch(repository) == "add-limit"
    git(repository, "switch", "--quiet", "--detach")
    assert current_branch(repository) is None


def test_head_commit_is_the_checked_out_commit_or_none_before_the_first(
    repository: Path,
) -> None:
    assert head_commit(repository) is None
    commit(repository, "a.txt", "2026-01-10T09:00:00+00:00")
    sha = head_commit(repository)
    assert sha is not None
    assert len(sha) == 40


def test_last_changed_gives_each_folders_newest_commit(repository: Path) -> None:
    commit(repository, "waymark/changes/add-limit/proposal.md", "2026-01-10T09:00:00+00:00")
    commit(repository, "waymark/changes/add-order/proposal.md", "2026-01-12T09:00:00+00:00")
    commit(repository, "waymark/changes/add-limit/tasks.md", "2026-02-01T09:00:00+00:00")
    commit(repository, "waymark/changes/add-limiter/tasks.md", "2026-03-01T09:00:00+00:00")
    (repository / "waymark/changes/add-paging").mkdir()
    found = last_changed(
        repository,
        ["waymark/changes/add-limit", "waymark/changes/add-order", "waymark/changes/add-paging"],
    )
    assert found == {
        "waymark/changes/add-limit": datetime.datetime(2026, 2, 1, 9, tzinfo=datetime.UTC),
        "waymark/changes/add-order": datetime.datetime(2026, 1, 12, 9, tzinfo=datetime.UTC),
    }


def test_last_changed_outside_a_repository_is_empty(tmp_path: Path) -> None:
    assert last_changed(tmp_path / "missing", ["waymark/changes/add-limit"]) == {}
    assert last_changed(tmp_path, []) == {}


def test_tracked_lists_the_tracked_files_among_the_paths_given(repository: Path) -> None:
    commit(repository, ".claude/settings.json", "2026-01-01T00:00:00+00:00")
    commit(repository, ".waymark/hooks/commit-msg", "2026-01-02T00:00:00+00:00")
    commit(repository, "src/app.py", "2026-01-03T00:00:00+00:00")
    (repository / ".claude" / "skills").mkdir()
    (repository / ".claude" / "skills" / "untracked.md").write_text("x", encoding="utf-8")
    found = tracked(
        repository,
        [".claude/settings.json", ".claude/skills/untracked.md", ".waymark/hooks", "missing"],
    )
    assert found == (".claude/settings.json", ".waymark/hooks/commit-msg")


def test_tracked_takes_paths_literally(repository: Path) -> None:
    commit(repository, "wm-a/file.md", "2026-01-01T00:00:00+00:00")
    assert tracked(repository, ["wm-*"]) == ()


def test_tracked_with_nothing_given_or_outside_a_repository_is_empty(
    repository: Path, tmp_path: Path
) -> None:
    assert tracked(repository, []) == ()
    assert tracked(tmp_path / "elsewhere", ["a"]) == ()

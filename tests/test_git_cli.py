"""Real commits through the installed git hooks, which call wm from PATH."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import git_init
from waymark.cli import EXIT_OK, main

pytestmark = pytest.mark.skipif(shutil.which("wm") is None, reason="needs wm on PATH")


def commit(
    root: Path, message: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), "commit", "--quiet", "-m", message],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "project"
    git_init(root)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "sam@example.com"], check=True)
    monkeypatch.chdir(root)
    assert main(["init", "--tool", "claude-code"]) == EXIT_OK
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


def test_the_commit_message_hook_stops_a_message_that_isnt_conventional(repo: Path) -> None:
    refused = commit(repo, "Set up the record")
    assert refused.returncode != 0
    assert "The commit was stopped" in refused.stderr
    assert commit(repo, "chore: set up the record").returncode == 0


def test_the_pre_commit_hook_stops_a_commit_while_the_record_has_errors(repo: Path) -> None:
    assert commit(repo, "chore: set up the record").returncode == 0
    (repo / "waymark" / "specs").mkdir()
    (repo / "waymark" / "specs" / "Bad.md").write_text("# Bad\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    refused = commit(repo, "docs: add a spec")
    assert refused.returncode != 0
    assert "wm check finds" in refused.stderr


def test_the_hooks_warn_and_let_the_commit_through_when_wm_is_missing(repo: Path) -> None:
    folders = os.environ.get("PATH", "").split(os.pathsep)
    without = [
        folder
        for folder in folders
        if not any((Path(folder) / name).exists() for name in ("wm", "wm.exe"))
    ]
    env = {**os.environ, "PATH": os.pathsep.join(without)}
    done = commit(repo, "not conventional at all", env)
    assert done.returncode == 0, done.stderr
    assert "wm is not on PATH" in done.stderr


def test_a_clone_with_windows_line_endings_still_gets_working_hooks(
    repo: Path, tmp_path: Path
) -> None:
    assert commit(repo, "chore: set up the record").returncode == 0
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "-c", "core.autocrlf=true", "clone", "--quiet", str(repo), str(clone)],
        check=True,
        capture_output=True,
    )
    for name in ("commit-msg", "pre-commit"):
        assert b"\r" not in (clone / ".waymark" / "hooks" / name).read_bytes()
    subprocess.run(["git", "-C", str(clone), "config", "core.autocrlf", "true"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.name", "Sam Doe"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.email", "sam@example.com"], check=True)
    subprocess.run(
        ["git", "-C", str(clone), "config", "core.hooksPath", ".waymark/hooks"], check=True
    )
    (clone / "notes.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(clone), "add", "notes.txt"], check=True)
    refused = commit(clone, "not conventional")
    assert refused.returncode != 0
    assert "The commit was stopped" in refused.stderr

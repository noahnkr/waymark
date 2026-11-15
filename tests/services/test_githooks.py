"""The git hooks: installing them, and the checks they run."""

import datetime
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace
from waymark.record import ignore
from waymark.record.githooks import HOOKS_DIR, HOOKS_IGNORED, HooksState, hooks_status
from waymark.record.project import find_project
from waymark.record.record import load_record
from waymark.services import githooks, integration, setup
from waymark.services.atlas import register
from waymark.services.common import Refusal
from waymark.services.doctor import Status, doctor
from waymark.views import payloads, render
from waymark.views.style import Style

NOW = datetime.datetime(2026, 11, 13, tzinfo=datetime.UTC)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=True
    )
    return result.stdout


def hooks_path(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--local", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or None


def message(root: Path, text: str) -> str:
    path = root / ".git" / "COMMIT_EDITMSG"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    git_init(root)
    return root


def staged(root: Path) -> str:
    return git(root, "diff", "--cached", "--name-only")


def is_ignored(root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--no-index", "--", path],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def block(root: Path) -> list[str]:
    lines = (root / ignore.PATH).read_text(encoding="utf-8").splitlines()
    return lines[lines.index(ignore.BEGIN) + 1 : lines.index(ignore.END)]


def test_hooks_are_written_executable_and_used_by_this_clone_without_staging(
    repo: Path,
) -> None:
    lines = githooks.install(repo, record=False)
    assert f"created: {HOOKS_DIR}/commit-msg" in lines
    assert "created: .gitignore" in lines
    assert hooks_path(repo) == HOOKS_DIR
    assert staged(repo) == ""
    assert not any("commit them" in line for line in lines)
    assert (
        (repo / HOOKS_DIR / ".gitattributes")
        .read_text(encoding="utf-8")
        .endswith("* text eol=lf\n")
    )
    script = (repo / HOOKS_DIR / "commit-msg").read_bytes()
    assert script.startswith(b"#!/bin/sh\n")
    assert b"\r\n" not in script
    assert b'wm run-hook commit-msg "$1"' in script
    if sys.platform != "win32":
        for name in ("commit-msg", "pre-commit"):
            assert (repo / HOOKS_DIR / name).stat().st_mode & stat.S_IXUSR
    assert hooks_status(repo).state is HooksState.SET
    assert githooks.install(repo, record=False) == []


def test_installing_with_a_record_leaves_the_block_to_the_caller(repo: Path) -> None:
    githooks.install(repo, record=True)
    assert not (repo / ".gitignore").exists()
    assert staged(repo) == ""


def test_git_hooks_command_installs_the_hooks_and_keeps_them_out_of_git(repo: Path) -> None:
    done = integration.git_hooks(repo)
    assert f"created: {HOOKS_DIR}/commit-msg" in done.message
    assert "created: .gitignore" in done.message
    assert "core.hooksPath" in done.message
    said = [line for line in done.message.splitlines() if not line.startswith("created: ")]
    assert not any("commit" in line for line in said)
    assert hooks_path(repo) == HOOKS_DIR
    assert staged(repo) == ""
    assert block(repo) == [HOOKS_IGNORED]
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == "?? .gitignore\n"
    assert integration.git_hooks(repo).message == "The git hooks are installed and in use."


def test_git_hooks_works_when_the_waymark_folder_is_already_ignored(repo: Path) -> None:
    (repo / ".gitignore").write_text("/.waymark/\n", encoding="utf-8")
    done = integration.git_hooks(repo)
    assert "updated: .gitignore" in done.message
    assert staged(repo) == ""
    assert hooks_status(repo).state is HooksState.SET
    assert (repo / ".gitignore").read_text(encoding="utf-8").startswith("/.waymark/\n")
    assert block(repo) == [HOOKS_IGNORED]


def test_git_hooks_in_a_code_repo_lists_only_the_hooks(tmp_path: Path) -> None:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG.replace('"some-tool"', '"claude-code"'))
    git_init(atlas.root)
    code = tmp_path / "suite-api"
    git_init(code)
    register(atlas.root)
    (code / ".waymark").mkdir()
    (code / ".waymark" / "atlas.toml").write_text('atlas = "suite"\n', encoding="utf-8")
    integration.git_hooks(code)
    assert block(code) == [HOOKS_IGNORED]
    assert not is_ignored(code, ".waymark/atlas.toml")
    assert is_ignored(code, f"{HOOKS_DIR}/commit-msg")
    assert staged(code) == ""


def test_git_hooks_in_a_project_writes_the_full_block(repo: Path) -> None:
    Workspace(repo, CONFIG.replace('"some-tool"', '"claude-code"'))
    integration.git_hooks(repo)
    assert block(repo) == integration.ignore_patterns(("claude-code",), record=True)
    assert HOOKS_IGNORED in block(repo)
    assert staged(repo) == ""
    assert hooks_status(repo).state is HooksState.SET
    assert integration.git_hooks(repo).message == "The git hooks are installed and in use."


def test_git_hooks_refuses_a_project_whose_settings_cant_be_read(repo: Path) -> None:
    Workspace(repo, "not = [toml\n")
    with pytest.raises(Refusal, match="wm check"):
        integration.git_hooks(repo)
    assert not (repo / HOOKS_DIR).exists()


@pytest.mark.skipif(shutil.which("wm") is None, reason="needs wm on PATH")
def test_hooks_run_in_a_fresh_clone_after_git_hooks(repo: Path, tmp_path: Path) -> None:
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "app.py")
    git(repo, "-c", "user.email=sam@example.com", "commit", "--quiet", "-m", "chore: start")
    integration.git_hooks(repo)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "--quiet", str(repo), str(clone)], check=True)
    assert not (clone / HOOKS_DIR).exists()
    integration.git_hooks(clone)
    (clone / "notes.txt").write_text("x\n", encoding="utf-8")
    git(clone, "add", "notes.txt")
    identity = ["-c", "user.name=Sam Doe", "-c", "user.email=sam@example.com"]
    refused = subprocess.run(
        ["git", "-C", str(clone), *identity, "commit", "--quiet", "-m", "wip"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0
    assert "The commit was stopped" in refused.stderr


def test_hooks_warn_and_let_the_commit_through_without_wm() -> None:
    for name in ("commit-msg", "pre-commit"):
        text = Path(__file__).parents[2] / "src/waymark/record/templates" / f"hook-{name}"
        script = text.read_text(encoding="utf-8")
        assert "command -v wm" in script
        assert "is not on PATH" in script
        assert script.rstrip().endswith("exit 0")


@pytest.mark.parametrize(
    "setup_manager",
    [
        lambda root: (root / ".husky").mkdir(),
        lambda root: (root / ".pre-commit-config.yaml").write_text("repos: []\n"),
        lambda root: (root / "lefthook.yml").write_text("pre-commit: {}\n"),
        lambda root: git(root, "config", "core.hooksPath", ".githooks"),
        lambda root: (root / ".git" / "hooks" / "commit-msg").write_text("#!/bin/sh\n"),
    ],
)
def test_a_repository_with_another_hook_setup_is_not_taken_over(
    repo: Path, setup_manager: object
) -> None:
    assert callable(setup_manager)
    setup_manager(repo)
    before = hooks_path(repo)
    lines = githooks.install(repo, record=False)
    assert "not installed" in lines[0]
    assert 'wm run-hook commit-msg "$1"' in "\n".join(lines)
    assert integration.git_hooks(repo).message.startswith("Git hooks: not installed")
    assert not (repo / HOOKS_DIR).exists()
    assert not (repo / ".gitignore").exists()
    assert hooks_path(repo) == before
    assert hooks_status(repo).state is HooksState.MANAGED


def test_init_installs_the_hooks_and_names_the_ci_command(repo: Path) -> None:
    done = setup.init_project(repo, None, ())
    assert "core.hooksPath" in done.message
    assert '"wm ci"' in done.message
    assert hooks_status(repo).state is HooksState.SET


def test_a_clone_that_hasnt_set_the_hooks_path_is_warned(repo: Path) -> None:
    setup.init_project(repo, None, ())
    git(repo, "config", "--unset", "core.hooksPath")
    assert hooks_status(repo).state is HooksState.NOT_SET
    payload = payloads.status(load_record(find_project(repo)))
    assert payload["git_hooks"] == "not-set"
    assert "wm git-hooks" in render.to_text(payload, Style())
    checks = {check.name: check for check in doctor(repo).checks}
    assert checks["git hooks"].status is Status.WARNING
    assert "wm git-hooks" in checks["git hooks"].message


def test_update_sets_the_hooks_path_again(repo: Path) -> None:
    setup.init_project(repo, None, ())
    git(repo, "config", "--unset", "core.hooksPath")
    done = integration.update(repo)
    assert "core.hooksPath" in done.message
    assert hooks_status(repo).state is HooksState.SET


def test_commit_message_check_uses_the_projects_scopes(repo: Path) -> None:
    Workspace(repo, CONFIG + 'commit_scopes = ["cli", "record"]\n')
    githooks.check_commit_message(repo, message(repo, "fix(cli): x\n"))
    with pytest.raises(Refusal, match='"views" is not one of'):
        githooks.check_commit_message(repo, message(repo, "fix(views): x\n"))
    with pytest.raises(Refusal, match="The commit was stopped"):
        githooks.check_commit_message(repo, message(repo, "wip\n"))


def test_commit_message_check_outside_a_project_accepts_any_scope(repo: Path) -> None:
    githooks.check_commit_message(repo, message(repo, "fix(anything): x\n"))
    with pytest.raises(Refusal):
        githooks.check_commit_message(repo, message(repo, "Fixed it\n"))


def test_code_repo_takes_its_scopes_from_its_atlas(tmp_path: Path) -> None:
    scoped = (CONFIG + 'commit_scopes = ["api"]\n' + ATLAS_CONFIG.removeprefix(CONFIG)).replace(
        '"some-tool"', '"claude-code"'
    )
    atlas = Workspace(tmp_path / "atlas", scoped)
    git_init(atlas.root)
    code = tmp_path / "suite-api"
    git_init(code)
    register(atlas.root)
    with pytest.raises(Refusal, match='"web" is not one of'):
        githooks.check_commit_message(code, message(code, "fix(web): x\n"))


def test_pre_commit_checks_the_record_only_when_the_commit_touches_it(repo: Path) -> None:
    project = Workspace(repo)
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    project.write("specs/Bad.md", "# Bad\n")
    git(repo, "add", "app.py")
    githooks.check_staged_record(repo, NOW)
    git(repo, "add", "waymark")
    with pytest.raises(Refusal, match=r"wm check finds \d+ error"):
        githooks.check_staged_record(repo, NOW)
    (repo / "waymark" / "specs" / "Bad.md").unlink()
    git(repo, "add", "-A")
    githooks.check_staged_record(repo, NOW)


def test_pre_commit_in_a_code_repo_does_nothing(repo: Path) -> None:
    (repo / "waymark").mkdir()
    (repo / "waymark" / "notes.md").write_text("x\n", encoding="utf-8")
    git(repo, "add", "-A")
    githooks.check_staged_record(repo, NOW)


def test_git_hooks_command_needs_a_git_repository(tmp_path: Path) -> None:
    with pytest.raises(Refusal, match="not in one"):
        integration.git_hooks(tmp_path)

"""The ``wm`` command runs, and follows the exit-code contract."""

import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import ClassVar

import pytest

from tests.conftest import git_init
from tests.support import Workspace, proposal
from waymark import __version__, cli
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main
from waymark.services import setup
from waymark.views.terminal import RawModeUnavailable


def run_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "waymark", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_exit_codes_are_0_success_1_refused_2_usage() -> None:
    assert (EXIT_OK, EXIT_REFUSED, EXIT_USAGE) == (0, 1, 2)


def test_wm_without_arguments_prints_help_and_exits_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: wm")
    assert captured.err == ""


def test_wm_version_prints_the_package_version_and_exits_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == EXIT_OK
    assert capsys.readouterr().out.strip() == f"wm {__version__}"


def test_wm_usage_error_exits_2_and_says_what_is_wrong(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--no-such-option"])
    assert exit_info.value.code == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--no-such-option" in captured.err


def test_wm_unknown_command_exits_2() -> None:
    result = run_module("no-such-command")
    assert result.returncode == EXIT_USAGE
    assert "no-such-command" in result.stderr


def test_wm_runs_as_a_module() -> None:
    result = run_module("--version")
    assert result.returncode == EXIT_OK
    assert result.stdout.strip() == f"wm {__version__}"


def test_wm_command_is_installed_and_runs() -> None:
    scripts = Path(sysconfig.get_path("scripts"))
    candidates = [scripts / "wm", scripts / "wm.exe"]
    installed = [path for path in candidates if path.exists()]
    assert installed, f"no wm command in {scripts}"
    result = subprocess.run(
        [str(installed[0]), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == EXIT_OK
    assert result.stdout.strip() == f"wm {__version__}"


def test_archive_takes_built_and_differs_not_outcome(capsys: pytest.CaptureFixture[str]) -> None:
    """Requirement "Structured outcome": the options of wm archive."""
    with pytest.raises(SystemExit):
        main(["archive", "--help"])
    usage = capsys.readouterr().out
    assert "--built" in usage
    assert "--differs" in usage
    assert "--outcome" not in usage
    with pytest.raises(SystemExit) as exit_info:
        main(["archive", "add-limit", "--outcome", "Done."])
    assert exit_info.value.code == EXIT_USAGE


def test_init_help_says_it_also_sets_up_a_clone(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["init", "--help"])
    assert "set up this machine in a clone that has one" in capsys.readouterr().out


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def signed(root: Path) -> None:
    for key, value in (("user.name", "Sam Doe"), ("user.email", "sam@example.com")):
        assert git(root, "config", key, value).returncode == 0


def test_wm_init_in_a_fresh_clone_sets_it_up_with_nothing_to_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenarios: New project, Fresh clone."""
    origin = tmp_path / "origin"
    origin.mkdir()
    assert git(origin, "init", "--quiet").returncode == 0
    signed(origin)
    monkeypatch.chdir(origin)
    assert main(["init", "--tool", "claude-code"]) == EXIT_OK
    new = git(origin, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()
    assert {line[3:].split("/")[0] for line in new} == {"waymark", ".gitignore"}
    assert git(origin, "add", "-A").returncode == 0
    assert git(origin, "commit", "--quiet", "-m", "chore: set up the record").returncode == 0

    clone = tmp_path / "clone"
    cloned = subprocess.run(
        ["git", "clone", "--quiet", str(origin), str(clone)], capture_output=True, check=False
    )
    assert cloned.returncode == 0, cloned.stderr
    signed(clone)
    settings = git(clone, "config", "--local", "--list").stdout
    monkeypatch.chdir(clone)
    assert main(["init"]) == EXIT_OK

    assert (clone / ".claude" / "settings.json").is_file()
    assert git(clone, "config", "--local", "--list").stdout == settings
    assert not (clone / ".waymark").exists()
    assert git(clone, "status", "--porcelain", "--untracked-files=all").stdout == ""


@pytest.mark.parametrize("command", ["git-hooks", "run-hook"])
def test_the_git_hook_commands_are_gone(command: str) -> None:
    result = run_module(command)
    assert result.returncode == EXIT_USAGE
    assert "invalid choice" in result.stderr


def test_wm_update_leaves_the_git_hooks_wm_0_1_1_installed_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clone set up by 0.1.1 keeps its core.hooksPath and .waymark/hooks/."""
    root = tmp_path / "project"
    root.mkdir()
    assert git(root, "init", "--quiet").returncode == 0
    signed(root)
    monkeypatch.chdir(root)
    assert main(["init", "--tool", "claude-code"]) == EXIT_OK
    hooks = root / ".waymark" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("commit-msg", "pre-commit"):
        (hooks / name).write_text(f"#!/bin/sh\nwm run-hook {name}\n", encoding="utf-8")
    assert git(root, "config", "core.hooksPath", ".waymark/hooks").returncode == 0
    before = {path.name: path.read_bytes() for path in hooks.iterdir()}
    capsys.readouterr()

    assert main(["update"]) == EXIT_OK

    assert "Everything is up to date." in capsys.readouterr().out
    assert git(root, "config", "--local", "core.hooksPath").stdout.strip() == ".waymark/hooks"
    assert {path.name: path.read_bytes() for path in hooks.iterdir()} == before


def test_wm_note_and_by_write_records(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """wm note writes a (note) record, and --by names who wrote a record."""
    project.write(
        "config.toml",
        project.read("config.toml"),
    )
    project.change()
    monkeypatch.chdir(project.root)
    assert main(["accept", "add-limit"]) == EXIT_OK
    assert main(["note", "add-limit", "1.2", "half done", "--by", "Ada Lovelace"]) == EXIT_OK
    assert main(["block", "add-limit", "1.2", "the key", "--by", "Ada: the planner"]) == (
        EXIT_REFUSED
    )
    tasks = project.read("changes/add-limit/tasks.md")
    assert " by Ada Lovelace: half done\n" in tasks
    assert "(note) " in tasks
    assert "(blocked)" not in tasks
    assert 'holds ": "' in capsys.readouterr().err


def test_wm_check_fix_reports_what_it_fixed(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """wm check --fix names each fixed file, then reports the check."""
    project.change(proposal_text=proposal().replace("Paging.", "Paging.   "))
    monkeypatch.chdir(project.root)
    assert main(["check", "--fix"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Fixed changes/add-limit/proposal.md: trailing spaces." in out
    assert main(["check", "--fix"]) == EXIT_OK
    assert "Nothing to fix" in capsys.readouterr().out
    assert main(["check", "--fix", "--json"]) == EXIT_REFUSED


def test_scenario_error_that_cant_be_fixed(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = proposal().replace("Paging.", "Paging, see [the plan](missing.md).  ")
    project.change(proposal_text=broken)
    monkeypatch.chdir(project.root)
    assert main(["check", "--fix"]) == EXIT_REFUSED
    out = capsys.readouterr().out
    assert "trailing spaces" in out
    assert "broken-link" in out
    assert "[the plan](missing.md)" in project.read("changes/add-limit/proposal.md")


def test_wm_new_change_takes_a_milestone(
    project: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    project.write(
        "milestones/faster-search/milestone.md",
        "# Faster search\n\n## Goal\n\nFast.\n\n## Done when\n\n- fast\n\n"
        "## Non-goals\n\n- caching\n\n## Roadmap\n\n- add-limit: cap the results\n",
    )
    monkeypatch.chdir(project.root)
    assert main(["new", "change", "add-limit", "--milestone", "faster-search"]) == EXIT_OK
    assert "- Milestone: faster-search\n" in project.read("changes/add-limit/proposal.md")
    assert main(["new", "change", "add-cache", "--milestone", "no-such-one"]) == EXIT_REFUSED
    assert not project.path("changes/add-cache").exists()
    assert main(["new", "milestone", "better-ranking", "--milestone", "x"]) == EXIT_REFUSED
    assert not project.path("milestones/better-ranking").exists()


def test_wm_roadmap_commands(project: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    project.write(
        "milestones/faster-search/milestone.md",
        "# Faster search\n\n## Goal\n\nFast.\n\n## Done when\n\n- fast\n\n"
        "## Non-goals\n\n- caching\n\n## Roadmap\n\n- add-limit: cap the results\n",
    )
    monkeypatch.chdir(project.root)
    add = ["roadmap", "add", "faster-search", "add-cache", "cache hot queries", "--by", "Ada"]
    assert main(add) == EXIT_OK
    assert main(["roadmap", "move", "faster-search", "add-cache", "--first"]) == EXIT_OK
    assert main(["roadmap", "move", "faster-search", "add-cache", "--after", "add-limit"]) == (
        EXIT_OK
    )
    assert main(["roadmap", "drop", "faster-search", "add-cache", "--reason", "fast"]) == EXIT_OK
    text = project.read("milestones/faster-search/milestone.md")
    assert "- (added) " in text
    assert "add-cache by Ada: cache hot queries" in text
    assert main(["roadmap", "drop", "faster-search", "add-limit", "--reason", "x"]) == EXIT_OK
    for usage in (
        ["roadmap", "drop", "faster-search", "add-limit"],
        ["roadmap", "move", "faster-search", "add-limit"],
        ["roadmap", "move", "faster-search", "add-limit", "--first", "--after", "add-x"],
    ):
        with pytest.raises(SystemExit) as stopped:
            main(usage)
        assert stopped.value.code == EXIT_USAGE


def test_wm_new_change_takes_after(project: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project.root)
    assert main(["new", "change", "add-limit"]) == EXIT_OK
    assert main(["new", "change", "add-paging", "--after", "add-limit"]) == EXIT_OK
    assert "- After: add-limit\n" in project.read("changes/add-paging/proposal.md")
    assert main(["new", "exploration", "paging", "--after", "add-limit"]) == EXIT_REFUSED
    assert not project.path("explorations/paging.md").exists()


def test_wm_new_resource_and_its_kind(project: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project.root)
    assert main(["new", "resource", "stripe", "service"]) == EXIT_OK
    assert "- Kind: service\n" in project.read("resources/stripe.md")
    assert main(["new", "resource", "mailgun"]) == EXIT_REFUSED
    assert not project.path("resources/mailgun.md").exists()
    for kind in ("change", "milestone", "exploration"):
        assert main(["new", kind, "add-limit", "service"]) == EXIT_REFUSED
    assert not project.path("changes/add-limit").exists()
    assert not project.path("explorations/add-limit.md").exists()


# The interactive wm init --------------------------------------------------------------------


class FakeTerminal:
    """A raw terminal that hands out queued key names and keeps what was drawn."""

    keys: ClassVar[list[str]] = []
    drawn: ClassVar[list[str]] = []
    entered: ClassVar[list[bool]] = []

    def __enter__(self) -> "FakeTerminal":
        FakeTerminal.entered.append(True)
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def draw(self, lines: list[str]) -> None:
        FakeTerminal.drawn.extend(lines)

    def finish(self) -> None:
        pass

    def key_waiting(self, timeout: float) -> bool:
        del timeout
        return bool(FakeTerminal.keys)

    def read_key(self) -> str:
        assert FakeTerminal.keys, "the flow asked for more keys than the test gave"
        return FakeTerminal.keys.pop(0)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh git repository as the current folder, on a terminal with a fake raw mode."""
    root = tmp_path / "repo"
    git_init(root)
    monkeypatch.chdir(root)
    monkeypatch.setattr(cli, "_on_a_terminal", lambda: True)
    monkeypatch.setattr(cli, "RawTerminal", FakeTerminal)
    FakeTerminal.keys.clear()
    FakeTerminal.drawn.clear()
    FakeTerminal.entered.clear()
    return root


def init_with(keys: list[str], capsys: pytest.CaptureFixture[str], *flags: str) -> tuple[int, str]:
    FakeTerminal.keys[:] = keys
    code = main(["init", *flags])
    return code, capsys.readouterr().out


def files_under(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


CANCELED = "Setup canceled. Nothing was written."
WELCOME = ["enter"]
PROJECT = ["enter"]
KEEP_TOOLS = ["enter"]
YES = ["enter"]


def test_scenario_project_with_claude_code_and_ci(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Requirement "Interactive init"."""
    code, out = init_with([*WELCOME, *PROJECT, *KEEP_TOOLS, *YES], capsys)
    assert code == EXIT_OK
    assert (repo / "waymark" / "config.toml").is_file()
    assert (repo / ".claude" / "settings.json").is_file()
    assert (repo / ".github" / "workflows" / "waymark.yml").is_file()
    assert "Created:" in out
    assert "  .github/workflows/waymark.yml" in out
    assert out.rstrip().splitlines()[-1].startswith("Next: run the wm-kickoff skill")
    drawn = "\n".join(FakeTerminal.drawn)
    assert "Leave a trail your agents can follow." in drawn
    assert "Repository" in drawn


def test_scenario_atlas(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    keys = [*WELCOME, "down", "enter", *"shop-platform", "enter", *KEEP_TOOLS, "n"]
    code, _ = init_with(keys, capsys)
    assert code == EXIT_OK
    other = tmp_path / "other"
    git_init(other)
    setup.init_project(other, atlas="shop-platform")
    asked = (repo / "waymark" / "config.toml").read_text(encoding="utf-8")
    flagged = (other / "waymark" / "config.toml").read_text(encoding="utf-8")
    assert asked == flagged
    assert not (repo / ".github").exists()


def test_invalid_atlas_name_keeps_the_question_open(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    keys = [*WELCOME, "down", "enter", *"shop", "space", *"platform", "enter", "escape"]
    code, out = init_with(keys, capsys)
    assert code == EXIT_REFUSED
    assert "can't be an atlas name" in "\n".join(FakeTerminal.drawn)
    assert not (repo / "waymark").exists()
    assert out.rstrip().endswith(CANCELED)


def test_scenario_tool_detected(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Requirement "Agent tools to choose from"."""
    (repo / ".claude").mkdir()
    init_with([*WELCOME, *PROJECT, "escape"], capsys)
    marks = ("  → ✓ Claude Code  found", "  -> x Claude Code  found")
    assert any(mark in FakeTerminal.drawn for mark in marks)


def test_scenario_canceled_at_the_tools(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Requirement "Canceled init writes nothing"."""
    before = files_under(repo)
    code, out = init_with([*WELCOME, *PROJECT, "escape"], capsys)
    assert code == EXIT_REFUSED
    assert files_under(repo) == before
    assert out.rstrip().endswith(CANCELED)


def test_escape_at_the_welcome_cancels(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = init_with(["escape"], capsys)
    assert code == EXIT_REFUSED
    assert not (repo / "waymark").exists()
    assert out.rstrip().endswith(CANCELED)


def test_scenario_run_by_an_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Requirement "Init without questions": output piped, nothing asked."""
    root = tmp_path / "repo"
    git_init(root)
    monkeypatch.chdir(root)
    assert main(["init"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Leave a trail" not in out
    assert "Created:" not in out
    assert (root / "waymark" / "config.toml").is_file()
    assert (root / ".claude" / "settings.json").is_file()


def test_scenario_yes_flag_on_a_terminal(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = init_with([], capsys, "--yes")
    assert code == EXIT_OK
    assert FakeTerminal.entered == []
    assert FakeTerminal.drawn == []
    assert "Leave a trail" not in out
    assert (repo / ".claude" / "settings.json").is_file()
    assert not (repo / ".github").exists()


def test_flags_skip_the_questions(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _ = init_with([], capsys, "--tool", "claude-code")
    assert code == EXIT_OK
    assert FakeTerminal.entered == []


def test_scenario_clone_on_a_terminal(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", "--yes"]) == EXIT_OK
    capsys.readouterr()
    record = {k: v for k, v in files_under(repo).items() if k.startswith("waymark/")}
    shutil.rmtree(repo / ".claude" / "skills")
    code, out = init_with(WELCOME, capsys)
    assert code == EXIT_OK
    assert FakeTerminal.keys == []
    drawn = "\n".join(FakeTerminal.drawn)
    assert "Leave a trail your agents can follow." in drawn
    assert "What is this repository?" not in drawn
    assert any((repo / ".claude" / "skills").iterdir())
    after = {k: v for k, v in files_under(repo).items() if k.startswith("waymark/")}
    assert after == record
    assert "Created:" not in out


def test_questions_by_line_without_raw_mode(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Requirement "Questions without raw mode": the whole flow at a line."""

    class NoRawMode:
        def __enter__(self) -> None:
            raise RawModeUnavailable("no console")

        def __exit__(self, *_: object) -> None:
            pass

    monkeypatch.setattr(cli, "RawTerminal", NoRawMode)
    typed = iter(["", "2", "shop-platform", "", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(typed))
    assert main(["init"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "What is the atlas's name?" in out
    assert "  2. An atlas  (a record that several code repos share)" in out
    config = (repo / "waymark" / "config.toml").read_text(encoding="utf-8")
    assert '"shop-platform"' in config

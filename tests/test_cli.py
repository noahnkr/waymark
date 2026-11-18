"""The ``wm`` command runs, and follows the exit-code contract."""

import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

from tests.support import Workspace, proposal
from waymark import __version__
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main


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

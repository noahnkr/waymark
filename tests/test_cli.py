"""The ``wm`` command runs, and follows the exit-code contract."""

import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

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


@pytest.mark.skipif(shutil.which("wm") is None, reason="the git hooks call wm from PATH")
def test_wm_init_in_a_fresh_clone_sets_it_up_with_nothing_to_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenarios: New project, Fresh clone, Hooks run after a clone."""
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
    monkeypatch.chdir(clone)
    assert main(["init"]) == EXIT_OK

    assert (clone / ".claude" / "settings.json").is_file()
    assert git(clone, "config", "core.hooksPath").stdout.strip() == ".waymark/hooks"
    assert git(clone, "status", "--porcelain", "--untracked-files=all").stdout == ""
    (clone / "notes.txt").write_text("x\n", encoding="utf-8")
    assert git(clone, "add", "notes.txt").returncode == 0
    refused = git(clone, "commit", "--quiet", "-m", "wip")
    assert refused.returncode != 0
    assert "The commit was stopped" in refused.stderr

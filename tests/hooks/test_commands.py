"""Reading shell commands for the guard rails."""

import pytest

from waymark.hooks.commands import (
    commits_or_pushes,
    invocations,
    state_change,
    wm_calls,
    writing_wm_call,
)


def test_programs_in_a_command_line_are_found_in_order() -> None:
    calls = invocations("cd src && git status; wm show add-limit | head -5")
    assert [(call.program, call.subcommand) for call in calls] == [
        ("cd", "src"),
        ("git", "status"),
        ("wm", "show"),
        ("head", None),
    ]


@pytest.mark.parametrize(
    "command",
    [
        "wm accept add-limit",
        "wm.exe accept add-limit",
        "/usr/local/bin/wm accept add-limit",
        'C:\\Tools\\wm.exe accept "add-limit"',
        "uv run wm accept add-limit",
        "uv run --no-sync wm accept add-limit",
        "python -m waymark accept add-limit",
        "py -m waymark accept add-limit",
        "FOO=1 env wm accept add-limit",
        "git status && wm accept add-limit",
    ],
)
def test_wm_is_recognized_however_it_is_started(command: str) -> None:
    (call,) = wm_calls(command)
    assert (call.program, call.subcommand) == ("wm", "accept")


def test_text_that_only_mentions_wm_is_not_a_wm_command() -> None:
    assert wm_calls('echo "run wm accept add-limit yourself"') == ()
    assert wm_calls("grep -r 'wm accept' docs") == ()


@pytest.mark.parametrize(
    "command",
    [
        "wm status",
        "wm show add-limit --json",
        "wm context add-limit 1.1 --for implement",
        "wm --version",
    ],
)
def test_reading_wm_commands_do_not_write(command: str) -> None:
    assert writing_wm_call(command) is None


@pytest.mark.parametrize(
    ("command", "subcommand"),
    [
        ("wm tick add-limit 1.1", "tick"),
        ("wm status && wm archive add-limit --outcome done", "archive"),
        ("wm new change add-order", "new"),
        ("wm update", "update"),
    ],
)
def test_writing_wm_commands_are_found(command: str, subcommand: str) -> None:
    found = writing_wm_call(command)
    assert found is not None
    assert found.subcommand == subcommand


def test_commits_and_pushes_are_found() -> None:
    assert commits_or_pushes('git add -A && git commit -m "feat: x"') is not None
    assert commits_or_pushes("git -C repo push origin main") is not None
    assert commits_or_pushes("git -c user.name=x commit -m y") is not None
    assert commits_or_pushes("git push") is not None
    assert commits_or_pushes("git status; git log --oneline; git diff") is None


@pytest.mark.parametrize(
    "command",
    [
        "pytest -q",
        "git diff HEAD~1",
        "git log --oneline | head -20",
        "cat src/app.py",
        "npm test 2>&1",
        "ls -la > /dev/null",
        "python -m pytest tests 2>/dev/null",
        "grep -rn 'limit' src",
    ],
)
def test_read_only_commands_change_no_state(command: str) -> None:
    assert state_change(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf build",
        "git checkout main",
        "git stash",
        "sed -i 's/a/b/' src/app.py",
        "echo fixed > src/app.py",
        "cat notes >> log.txt",
        "pip install requests",
        "npm install",
        "mv a b",
        "Remove-Item build -Recurse",
        "pytest -q && touch done.flag",
    ],
)
def test_state_changing_commands_are_named(command: str) -> None:
    assert state_change(command) is not None

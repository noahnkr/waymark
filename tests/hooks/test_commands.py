"""Reading shell commands for the guard rails."""

import argparse

import pytest

from waymark.cli import build_parser
from waymark.hooks.commands import (
    READ_COMMANDS,
    CommitMessage,
    commit_messages,
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


@pytest.mark.parametrize(
    "command",
    ["wm doctor", "wm atlas doctor --json", "wm pr add-limit --repo api", "wm ls specs --from x"],
)
def test_reading_commands_added_later_are_not_mistaken_for_writes(command: str) -> None:
    assert writing_wm_call(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "wm atlas register",
        "wm atlas point suite",
        "wm ci",
        "wm atlas",
        'wm note add-limit 1.2 "half done"',
    ],
)
def test_writing_commands_added_later_are_found(command: str) -> None:
    assert writing_wm_call(command) is not None


WRITES = frozenset(
    {
        "init",
        "update",
        "new",
        "accept",
        "tick",
        "block",
        "gap",
        "note",
        "revise",
        "review",
        "verdict",
        "reopen",
        "resolve",
        "sync",
        "archive",
        "close",
        "roadmap",
        "exploration",
        "atlas",
        "ci",
    }
)


def test_every_command_is_known_to_read_or_to_write() -> None:
    """A new command must be sorted into one or the other, or delegated agents misjudge it."""
    parser = build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    names = set(action.choices)
    assert names == READ_COMMANDS | WRITES
    assert not READ_COMMANDS & WRITES


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ('git commit -m "feat: add a limit"', "feat: add a limit"),
        ("git commit -m 'fix: x; y & z | w'", "fix: x; y & z | w"),
        ('git commit --message "docs: a"', "docs: a"),
        ('git commit --message="docs: a"', "docs: a"),
        ('git commit -m"fix: attached"', "fix: attached"),
        ('git commit -am "fix: all"', "fix: all"),
        ('git commit -m "feat: a" -m "The body."', "feat: a\n\nThe body."),
        ('git commit -m "feat: a\n\nThe body."', "feat: a\n\nThe body."),
        ('git -C repo commit -m "fix: x"', "fix: x"),
        ('git add -A && git commit -m "fix: x" && git push', "fix: x"),
        ("uv run git commit -m wip", "wip"),
    ],
)
def test_commit_message_from_the_message_option(command: str, message: str) -> None:
    assert commit_messages(command) == [CommitMessage(text=message)]


@pytest.mark.parametrize(
    ("opening", "tag"),
    [
        ("<<'EOF'", "EOF"),
        ('<<"EOF"', "EOF"),
        ("<<EOF", "EOF"),
        ("<< 'EOF'", "EOF"),
        ("<<'MSG'", "MSG"),
    ],
)
def test_commit_message_from_a_here_document(opening: str, tag: str) -> None:
    command = (
        f'git add -A && git commit -m "$(cat {opening}\n'
        "feat(hooks): read commit messages\n\nWith a body; and & a pipe |.\n"
        f'{tag}\n)" && git status'
    )
    assert commit_messages(command) == [
        CommitMessage(text="feat(hooks): read commit messages\n\nWith a body; and & a pipe |.")
    ]


def test_commit_message_from_an_indented_here_document() -> None:
    command = "git commit -m \"$(cat <<-'EOF'\n\twip\n\tEOF\n)\""
    assert commit_messages(command) == [CommitMessage(text="wip")]


def test_unquoted_here_document_that_expands_is_unreadable() -> None:
    command = 'git commit -m "$(cat <<EOF\nfix: $SUBJECT\nEOF\n)"'
    assert commit_messages(command) == [None]


@pytest.mark.parametrize(
    ("command", "path"),
    [
        ("git commit -F msg.txt", "msg.txt"),
        ("git commit --file=msg.txt", "msg.txt"),
        ("git commit --file msg.txt", "msg.txt"),
        ("git commit -aF msg.txt", "msg.txt"),
        ("git add . && git commit -F C:\\Users\\me\\msg.txt", "C:/Users/me/msg.txt"),
        ('git commit -F "C:\\Users\\me\\commit msg.txt"', "C:/Users/me/commit msg.txt"),
    ],
)
def test_commit_message_file_is_given_as_a_path(command: str, path: str) -> None:
    assert commit_messages(command) == [CommitMessage(file=path)]


@pytest.mark.parametrize(
    "command",
    [
        "git commit",
        "git commit -a",
        "git commit --amend --no-edit",
        'git commit -m "$(git log -1 --format=%s)"',
        'git commit -m "$SUBJECT"',
        "git commit -m `cat msg`",
        "git commit -F -",
        'git commit -m "x" -F msg.txt',
        "git commit --fixup HEAD~1",
        "git commit -C HEAD",
        "git commit -m",
        'git commit -m "fix: unbalanced',
    ],
)
def test_commit_message_that_cant_be_read_is_none(command: str) -> None:
    assert commit_messages(command) == [None]


def test_each_commit_in_a_command_line_has_an_entry() -> None:
    command = 'git commit -m "fix: one"; git commit && git commit -F notes.txt'
    assert commit_messages(command) == [
        CommitMessage(text="fix: one"),
        None,
        CommitMessage(file="notes.txt"),
    ]


def test_commands_without_a_commit_have_no_messages() -> None:
    assert commit_messages("git status && git push && echo 'git commit -m wip'") == []

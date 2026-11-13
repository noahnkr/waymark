"""The commit-message check: conventional commits, with the project's scopes."""

import pytest

from waymark.record.commits import TYPES, commit_problem


@pytest.mark.parametrize(
    "message",
    [
        "feat: add a result limit",
        "fix(search): accept an empty query",
        "feat(api)!: drop the old endpoint",
        "docs: explain the limit\n\nThe body explains why.\n",
        "refactor: split the parser\n# Please enter the commit message for your changes.\n",
    ],
)
def test_conventional_commit_messages_pass(message: str) -> None:
    assert commit_problem(message) is None


def test_every_standard_type_is_accepted() -> None:
    assert TYPES == (
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    )
    for kind in TYPES:
        assert commit_problem(f"{kind}: do the thing") is None


@pytest.mark.parametrize(
    ("message", "problem"),
    [
        ("Add a result limit", "not a conventional commit summary"),
        ("feature: add a result limit", '"feature" is not a commit type'),
        ("Feat: add a result limit", "not a conventional commit summary"),
        ("feat:add a result limit", "one space after the colon"),
        ("feat(): add a result limit", "scope in parentheses is empty"),
        ("feat: ", "summary after the colon is empty"),
        ("feat: add a limit\nand more here", "Leave a blank line"),
        ("", "empty"),
        ("# only a comment\n", "empty"),
    ],
)
def test_messages_that_break_the_format_are_refused_with_how_to_fix_them(
    message: str, problem: str
) -> None:
    found = commit_problem(message)
    assert found is not None
    assert problem in found


def test_any_scope_passes_without_a_list() -> None:
    assert commit_problem("fix(anything): x") is None


def test_listed_scopes_limit_a_scope_given_but_dont_require_one() -> None:
    scopes = ("cli", "record")
    assert commit_problem("fix(cli): x", scopes) is None
    assert commit_problem("docs: update the readme", scopes) is None
    found = commit_problem("fix(views): x", scopes)
    assert found is not None
    assert '"views" is not one of this project\'s commit scopes (cli, record)' in found


@pytest.mark.parametrize(
    "message",
    [
        "Merge branch 'main' into add-limit",
        "Merge pull request #7 from someone/add-limit",
        'Revert "feat: add a result limit"\n\nThis reverts commit abc.',
        "fixup! feat: add a result limit",
        "squash! fix: x",
        "amend! fix: x",
    ],
)
def test_messages_git_writes_itself_pass(message: str) -> None:
    assert commit_problem(message, ("cli",)) is None


def test_lines_below_the_scissors_are_not_part_of_the_message() -> None:
    message = (
        "fix: a thing\n# ------------------------ >8 ------------------------\ndiff --git a/x b/x\n"
    )
    assert commit_problem(message) is None


def test_windows_line_endings_are_read_the_same() -> None:
    assert commit_problem("fix: a thing\r\n\r\nbody\r\n") is None
    found = commit_problem("fix: a thing\r\nbody\r\n")
    assert found is not None

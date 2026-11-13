"""The commit-message check: conventional commits, with the project's scopes if it lists any.

A message reads ``<type>(<scope>)!: <summary>``, where the scope and the ``!``
(a breaking change) are optional. When the project lists scopes, a scope
given must be one of them. Messages git writes itself pass as they are.
"""

import re

TYPES = (
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
"""The commit types the check accepts."""

_HEADER = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^()\s]*)\))?(?P<breaking>!)?:(?P<summary>.*)$"
)
_GIT_WRITTEN = ("Merge ", 'Revert "', "fixup! ", "squash! ", "amend! ")
_SCISSORS = "# ------------------------ >8 ------------------------"


def _lines(message: str) -> list[str]:
    """The message as git will record it: comments and everything below the scissors gone."""
    kept: list[str] = []
    for line in message.replace("\r\n", "\n").split("\n"):
        if line.startswith(_SCISSORS):
            break
        if not line.startswith("#"):
            kept.append(line.rstrip())
    while kept and not kept[0]:
        kept.pop(0)
    return kept


def commit_problem(  # noqa: PLR0911 - one return per rule
    message: str, scopes: tuple[str, ...] | None = None
) -> str | None:
    """What is wrong with a commit message, and how to fix it; None when it is fine."""
    lines = _lines(message)
    if not lines:
        return "The commit message is empty. Write one such as: feat: add a result limit"
    header = lines[0]
    if header.startswith(_GIT_WRITTEN):
        return None
    example = "<type>(<scope>): <summary>, for example: fix: accept an empty search query"
    match = _HEADER.match(header)
    if match is None:
        return (
            f'"{header}" is not a conventional commit summary. Write it as {example}. '
            f"Types: {', '.join(TYPES)}."
        )
    kind, scope = match["type"], match["scope"]
    if kind not in TYPES:
        return f'"{kind}" is not a commit type. Use one of: {", ".join(TYPES)}.'
    if scope is not None and not scope:
        return "The scope in parentheses is empty. Name a scope, or leave out the parentheses."
    if scope is not None and scopes is not None and scope not in scopes:
        return (
            f'"{scope}" is not one of this project\'s commit scopes ({", ".join(scopes)}). '
            "Use one of them, or leave the scope out."
        )
    if not match["summary"].strip():
        return f"The summary after the colon is empty. Write it as {example}."
    if not match["summary"].startswith(" "):
        return "Put one space after the colon, before the summary."
    if len(lines) > 1 and lines[1]:
        return "Leave a blank line between the summary and the rest of the message."
    return None

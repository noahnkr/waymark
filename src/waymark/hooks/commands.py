"""Reading a shell command well enough to apply the guard rails.

This is not a shell parser and not a security boundary. It finds the programs
a command line runs and their first argument, which is enough to stop the
mistakes and shortcuts the workflow rules out.
"""

import re
import shlex
from dataclasses import dataclass

READ_COMMANDS = frozenset(
    {"status", "inbox", "show", "ls", "check", "instructions", "context", "hook"}
)
"""The wm commands that never write."""

_SEPARATOR = re.compile(r"\|\||&&|[;\n|&]")
_WRAPPERS = frozenset({"sudo", "env", "command", "time", "nohup", "exec", "call", "start"})
_RUNNERS = frozenset({"uv", "uvx", "pipx", "poetry", "hatch"})
_PYTHON = re.compile(r"^(python[\d.]*|py)$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WINDOWS_SEPARATOR = re.compile(r"\\(?=[\w.])")
"""A backslash inside a Windows path, which a POSIX reading would swallow."""
_REDIRECT = re.compile(
    r"(?<![0-9&>])>>?(?!&)\s*(?!/dev/null\b|\$null\b|nul\b)[^\s>]", re.IGNORECASE
)

_GIT_WRITES = frozenset({"commit", "push"})
_GIT_STATE = frozenset(
    {
        "add",
        "am",
        "apply",
        "branch",
        "checkout",
        "cherry-pick",
        "clean",
        "commit",
        "merge",
        "mv",
        "pull",
        "push",
        "rebase",
        "reset",
        "restore",
        "revert",
        "rm",
        "stash",
        "switch",
        "tag",
        "worktree",
    }
)
_MUTATORS = frozenset(
    {
        "rm",
        "rmdir",
        "mv",
        "cp",
        "mkdir",
        "touch",
        "chmod",
        "chown",
        "ln",
        "dd",
        "truncate",
        "tee",
        "del",
        "erase",
        "move",
        "copy",
        "ren",
        "rename",
        "remove-item",
        "move-item",
        "copy-item",
        "new-item",
        "rename-item",
        "set-content",
        "add-content",
        "clear-content",
        "out-file",
    }
)
_PACKAGE_TOOLS = frozenset({"pip", "pip3", "npm", "yarn", "pnpm", "uv", "poetry", "cargo", "go"})
_PACKAGE_WRITES = frozenset(
    {"install", "uninstall", "add", "remove", "update", "upgrade", "publish", "sync", "lock", "get"}
)


@dataclass(frozen=True)
class Invocation:
    """One program a command line runs, its first plain argument, and all its arguments."""

    program: str
    subcommand: str | None
    arguments: tuple[str, ...]
    text: str


def _name(token: str) -> str:
    """A program's name without its folder or a Windows extension."""
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return re.sub(r"\.(exe|cmd|bat|ps1)$", "", name)


def _invocation(text: str) -> Invocation | None:
    try:
        tokens = shlex.split(_WINDOWS_SEPARATOR.sub("/", text), posix=True)
    except ValueError:
        tokens = text.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        name = _name(token)
        if _ASSIGNMENT.match(token) or name in _WRAPPERS or token.startswith("-"):
            index += 1
        elif name in _RUNNERS and tokens[index + 1 : index + 2] == ["run"]:
            index += 2
        elif _PYTHON.match(name) and tokens[index + 1 : index + 3] == ["-m", "waymark"]:
            tokens = ["wm", *tokens[index + 3 :]]
            index = 0
            break
        else:
            break
    if index >= len(tokens):
        return None
    arguments = tuple(tokens[index + 1 :])
    plain = list(arguments)
    while _name(tokens[index]) == "git" and plain[:1] in (["-C"], ["-c"]):
        plain = plain[2:]
    subcommand = next((arg for arg in plain if not arg.startswith("-")), None)
    return Invocation(_name(tokens[index]), subcommand, arguments, text.strip())


def invocations(command: str) -> tuple[Invocation, ...]:
    """Every program a command line runs, in order."""
    found = (_invocation(part) for part in _SEPARATOR.split(command) if part.strip())
    return tuple(invocation for invocation in found if invocation is not None)


def wm_calls(command: str) -> tuple[Invocation, ...]:
    """The wm commands in a command line."""
    return tuple(call for call in invocations(command) if call.program == "wm")


def writing_wm_call(command: str) -> Invocation | None:
    """The first wm command in a command line that writes, if any."""
    for call in wm_calls(command):
        if call.subcommand is not None and call.subcommand not in READ_COMMANDS:
            return call
    return None


def commits_or_pushes(command: str) -> Invocation | None:
    """The first git commit or push in a command line, if any."""
    for call in invocations(command):
        if call.program == "git" and call.subcommand in _GIT_WRITES:
            return call
    return None


def state_change(command: str) -> str | None:
    """What in a command line changes state, in a few words; None when nothing does."""
    if _REDIRECT.search(command):
        return "it writes to a file"
    for call in invocations(command):
        if call.program in _MUTATORS:
            return f'"{call.program}" changes files'
        if call.program == "git" and call.subcommand in _GIT_STATE:
            return f'"git {call.subcommand}" changes the repository'
        if call.program == "sed" and any(arg.startswith("-i") for arg in call.arguments):
            return '"sed -i" edits files in place'
        if call.program in _PACKAGE_TOOLS and call.subcommand in _PACKAGE_WRITES:
            return f'"{call.program} {call.subcommand}" changes what is installed'
    return None

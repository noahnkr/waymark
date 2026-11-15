"""Reading a shell command well enough to apply the guard rails.

This is not a shell parser and not a security boundary. It finds the programs
a command line runs and their first argument, which is enough to stop the
mistakes and shortcuts the workflow rules out.
"""

import re
import shlex
from dataclasses import dataclass

READ_COMMANDS = frozenset(
    {"status", "inbox", "show", "ls", "check", "instructions", "context", "hook", "doctor", "pr"}
)
"""The wm commands that never write."""

READ_GROUP_COMMANDS = {"atlas": frozenset({"doctor"})}
"""Commands in a group that never write, such as "wm atlas doctor"."""


def _reads(call: "Invocation") -> bool:
    if call.subcommand in READ_COMMANDS:
        return True
    reading = READ_GROUP_COMMANDS.get(call.subcommand or "")
    if reading is None:
        return False
    rest = [arg for arg in call.arguments if not arg.startswith("-")]
    return rest[1:2] != [] and rest[1] in reading


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
        if call.subcommand is not None and not _reads(call):
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


@dataclass(frozen=True)
class CommitMessage:
    """The message one git commit gives on its command line: the text, or the file it names."""

    text: str | None = None
    file: str | None = None


_HEREDOC = re.compile(
    r"\$\(\s*cat\s+<<(?P<dash>-?)[ \t]*(?P<quote>['\"]?)(?P<tag>[A-Za-z_][\w-]*)(?P=quote)"
    r"[ \t]*\n(?:(?P<body>.*?)\n)?[ \t]*(?P=tag)[ \t]*\n?\s*\)",
    re.DOTALL,
)
"""A "$(cat <<'EOF' ... EOF)" substitution, the usual way agents write a long message."""
_PLACEHOLDER = re.compile(r"\x00(\d+)\x00")
_EXPANDS = re.compile(r"\$\S|`")
"""Text the shell would expand: a variable, a command substitution or a backtick."""
_VALUE_FLAGS = "mFCct"
"""Short git commit options that take a value, attached or as the next argument."""
_OPTIONAL_VALUE_FLAGS = "Su"
"""Short git commit options whose value can only be attached."""
_UNREADABLE_OPTIONS = frozenset(
    {"--fixup", "--squash", "--template", "--reuse-message", "--reedit-message"}
)
"""Options that take the message from elsewhere: another commit, a template or an editor."""


def _heredoc_body(match: re.Match[str]) -> str | None:
    body = match.group("body") or ""
    if match.group("dash"):
        body = "\n".join(line.lstrip("\t") for line in body.split("\n"))
    if not match.group("quote") and _EXPANDS.search(body):
        return None
    return body


def _split_quoted(command: str) -> list[str]:
    """A command line's parts, split on ;, &, | and newlines outside quotes and $( )."""
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    index = 0
    while index < len(command):
        char = command[index]
        step = 1
        if quote == "'":
            quote = None if char == "'" else quote
        elif char == "\\":
            step = 2
        elif quote == '"':
            quote = None if char == '"' else quote
        elif char in "'\"":
            quote = char
        elif command.startswith("$(", index):
            depth += 1
            step = 2
        elif char == ")" and depth:
            depth -= 1
        elif char in ";&|\n" and not depth:
            parts.append("".join(current))
            current = []
            index += 1
            continue
        current.append(command[index : index + step])
        index += step
    parts.append("".join(current))
    return [part for part in parts if part.strip()]


def _commit_arguments(arguments: tuple[str, ...]) -> list[str]:
    """The arguments after "commit", past git's own options such as -C <dir>."""
    index = 0
    while index < len(arguments) and arguments[index] != "commit":
        index += 2 if arguments[index] in ("-C", "-c") else 1
    return list(arguments[index + 1 :])


def _message_options(arguments: list[str]) -> tuple[list[str], list[str]] | None:
    """The -m and -F values of a git commit, or None when its message comes from elsewhere."""
    messages: list[str] = []
    files: list[str] = []
    rest = iter(arguments)
    for argument in rest:
        if argument == "--":
            break
        if argument.startswith("--"):
            name, equals, value = argument.partition("=")
            if name in _UNREADABLE_OPTIONS:
                return None
            if name in ("--message", "--file"):
                found = value if equals else next(rest, None)
                if found is None:
                    return None
                (messages if name == "--message" else files).append(found)
        elif argument.startswith("-") and len(argument) > 1:
            for position, flag in enumerate(argument[1:], start=2):
                if flag in _OPTIONAL_VALUE_FLAGS:
                    break
                if flag in _VALUE_FLAGS:
                    found = argument[position:] or next(rest, None)
                    if found is None or flag not in "mF":
                        return None
                    (messages if flag == "m" else files).append(found)
                    break
    return messages, files


def _resolve(value: str, bodies: list[str | None]) -> str | None:
    """A value with its here-documents put back, or None when the shell would expand it."""
    pieces = _PLACEHOLDER.split(value)
    resolved: list[str] = []
    for position, piece in enumerate(pieces):
        if position % 2:
            body = bodies[int(piece)]
            if body is None:
                return None
            resolved.append(body)
        elif _EXPANDS.search(piece):
            return None
        else:
            resolved.append(piece)
    return "".join(resolved)


def _message_file(files: list[str], held: int) -> CommitMessage | None:
    """The one file a git commit names with -F, unless it is stdin or the shell expands it."""
    path = _resolve(files[0], [None] * held)
    if len(files) > 1 or path in (None, "-"):
        return None
    return CommitMessage(file=path)


def _commit_message(call: Invocation, bodies: list[str | None]) -> CommitMessage | None:
    try:
        shlex.split(_WINDOWS_SEPARATOR.sub("/", call.text), posix=True)
    except ValueError:
        return None
    options = _message_options(_commit_arguments(call.arguments))
    if options is None or all(options):
        return None
    messages, files = options
    if files:
        return _message_file(files, len(bodies))
    texts = [_resolve(message, bodies) for message in messages]
    if not texts or any(text is None for text in texts):
        return None
    return CommitMessage(text="\n\n".join(text for text in texts if text is not None))


def commit_messages(command: str) -> list[CommitMessage | None]:
    """The message of each git commit in a command line, in order; None where it can't be read.

    A message comes from -m or --message, several joined with blank lines as git
    joins them, with "$(cat <<'EOF' ... EOF)" read as its here-document. With -F
    or --file, the file's path is given instead. Any other substitution or a
    variable, or no message option at all, makes the message unreadable.
    """
    bodies: list[str | None] = []

    def hold(match: re.Match[str]) -> str:
        bodies.append(_heredoc_body(match))
        return f"\x00{len(bodies) - 1}\x00"

    held = _HEREDOC.sub(hold, command)
    found: list[CommitMessage | None] = []
    for part in _split_quoted(held):
        call = _invocation(part)
        if call is not None and call.program == "git" and call.subcommand == "commit":
            found.append(_commit_message(call, bodies))
    return found

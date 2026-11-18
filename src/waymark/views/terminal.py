"""The terminal under the prompts: raw keys, redraws in place, and a line fallback.

``RawTerminal`` reads one key at a time with the terminal in raw mode, through
``msvcrt`` on Windows and ``termios`` on POSIX, maps it to a key name the prompts
understand, and redraws a prompt in place. It always restores the terminal mode
and the cursor. Where raw mode can't be entered it raises ``RawModeUnavailable``,
and the caller asks the same questions with ``ask_by_line``: numbered choices
typed at a line, with the same defaults and validation.
"""

import os
import sys
from collections.abc import Callable
from types import TracebackType
from typing import Any, TextIO

from waymark.views.prompts import Checklist, Confirm, Outcome, Prompt, Select, TextInput
from waymark.views.style import ATTENTION, STRONG, Style, enable_escape_sequences

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
UP = "\x1b[{}A"
ERASE_LINE = "\x1b[2K"
NEWLINE = "\r\n"
"""Raw mode turns off the newline translation, so every line ends in a carriage return too."""

_CONTROL = {
    "\r": "enter",
    "\n": "enter",
    " ": "space",
    "\x08": "backspace",
    "\x7f": "backspace",
    "\x1b": "escape",
    "\x03": "escape",
    "\t": "tab",
}
"""Single characters that name a key on both platforms; Ctrl+C cancels, like Escape."""

_WINDOWS_ARROWS = {"H": "up", "P": "down", "K": "left", "M": "right"}
"""The second character ``msvcrt.getwch`` returns after an ``\\x00`` or ``\\xe0`` prefix."""

_POSIX_ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}
"""The final character of an ``ESC [`` or ``ESC O`` arrow sequence."""


class RawModeUnavailable(Exception):  # noqa: N818 - it names the situation, not an error
    """The terminal can't be put into raw mode; ask by line instead."""


def windows_key(first: str, read: Callable[[], str]) -> str:
    """The key name for what ``msvcrt.getwch`` returned, reading a second character if needed."""
    if first in ("\x00", "\xe0"):
        return _WINDOWS_ARROWS.get(read(), "unknown")
    return _CONTROL.get(first, first)


def posix_key(first: str, read_waiting: Callable[[], str | None]) -> str:
    """The key name for a character read from a POSIX terminal.

    ``read_waiting`` gives the next character only when one is already waiting,
    so a lone Escape isn't held up waiting for a sequence that never comes.
    """
    if first != "\x1b":
        return _CONTROL.get(first, first)
    second = read_waiting()
    if second not in ("[", "O"):
        return "escape"
    third = read_waiting()
    return _POSIX_ARROWS.get(third or "", "unknown")


class RawTerminal:
    """The terminal in raw mode, for one interactive session; use it as a context manager."""

    def __init__(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._saved: Any = None
        self._drawn = 0

    def __enter__(self) -> "RawTerminal":
        if not (self.stdin.isatty() and self.stdout.isatty()):
            raise RawModeUnavailable("Input and output must both be a terminal.")
        if sys.platform == "win32":
            try:
                import msvcrt  # noqa: PLC0415, F401 - Windows only
            except ImportError as error:
                raise RawModeUnavailable(str(error)) from error
            if not enable_escape_sequences():
                raise RawModeUnavailable("This console can't redraw in place.")
        else:
            import termios  # noqa: PLC0415 - POSIX only
            import tty  # noqa: PLC0415 - POSIX only

            try:
                descriptor = self.stdin.fileno()
                self._saved = termios.tcgetattr(descriptor)
                tty.setraw(descriptor)
            except (termios.error, OSError, ValueError) as error:
                raise RawModeUnavailable(str(error)) from error
        self.write(HIDE_CURSOR)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        try:
            if sys.platform != "win32" and self._saved is not None:
                import termios  # noqa: PLC0415 - POSIX only

                termios.tcsetattr(self.stdin.fileno(), termios.TCSADRAIN, self._saved)
        finally:
            self.write(SHOW_CURSOR)

    def write(self, text: str) -> None:
        self.stdout.write(text)
        self.stdout.flush()

    def read_key(self) -> str:
        """Wait for one key, and give its name."""
        if sys.platform == "win32":
            import msvcrt  # noqa: PLC0415 - Windows only

            key = windows_key(msvcrt.getwch(), msvcrt.getwch)
        else:
            first = os.read(self.stdin.fileno(), 1).decode(errors="replace")
            key = posix_key(first, self._waiting)
        return key

    def _waiting(self) -> str | None:
        """The next character when one is already waiting, else None."""
        if not self.key_waiting(0.05):
            return None
        return os.read(self.stdin.fileno(), 1).decode(errors="replace")

    def key_waiting(self, timeout: float) -> bool:
        """Whether a key arrives within ``timeout`` seconds, without reading it."""
        if sys.platform == "win32":
            import msvcrt  # noqa: PLC0415 - Windows only
            import time  # noqa: PLC0415

            deadline = time.monotonic() + timeout
            waiting = bool(msvcrt.kbhit())
            while not waiting and time.monotonic() < deadline:
                time.sleep(0.01)
                waiting = bool(msvcrt.kbhit())
        else:
            import select  # noqa: PLC0415 - POSIX only

            ready, _, _ = select.select([self.stdin.fileno()], [], [], timeout)
            waiting = bool(ready)
        return waiting

    def draw(self, lines: list[str]) -> None:
        """Draw lines in place of the ones drawn last."""
        text = UP.format(self._drawn) if self._drawn else ""
        text += "\r"
        text += NEWLINE.join(ERASE_LINE + line for line in lines)
        self.write(text)
        self._drawn = max(len(lines) - 1, 0)

    def finish(self) -> None:
        """Leave what was drawn on screen, and start the next drawing below it."""
        self.write(NEWLINE)
        self._drawn = 0


def ask(prompt: Prompt, terminal: RawTerminal, style: Style) -> Outcome:
    """Ask one question in raw mode: draw it, feed it keys until it is answered or canceled."""
    terminal.draw(prompt.render(style))
    while prompt.outcome is Outcome.OPEN:
        prompt.handle(terminal.read_key())
        terminal.draw(prompt.render(style))
    terminal.finish()
    return prompt.outcome


Reader = Callable[[str], str]
"""Reads a line after showing a prompt, as ``input`` does."""


def read_line(hint: str) -> str:
    """A line typed at the terminal, read with ``input`` when it is called."""
    return input(hint)


def ask_by_line(
    prompt: Prompt, style: Style, read: Reader = read_line, write: Callable[[str], None] = print
) -> Outcome:
    """Ask one question at a line: numbered choices, Enter for the default, as raw mode would.

    The answer is set on the same prompt and confirmed with Enter, so the
    prompt's own defaults and validation decide it. End of input or Ctrl+C cancels.
    """
    write(style.paint(prompt.question, STRONG))
    if isinstance(prompt, Select | Checklist):
        for number, choice in enumerate(prompt.choices, 1):
            note = f"  ({choice.note})" if choice.note else ""
            write(f"  {number}. {choice.label}{note}")
    while prompt.outcome is Outcome.OPEN:
        try:
            line = read(_line_hint(prompt)).strip()
        except (EOFError, KeyboardInterrupt):
            prompt.handle("escape")
            break
        problem = _answer(prompt, line)
        if problem is None:
            prompt.handle("enter")
            problem = prompt.reason
        if problem:
            write(style.paint(f"  {style.symbol('warning')} {problem}", ATTENTION))
    return prompt.outcome


def _line_hint(prompt: Prompt) -> str:
    """What to type, with the default in brackets."""
    if isinstance(prompt, Select):
        return f"Choose 1-{len(prompt.choices)} [{prompt.focus + 1}]: "
    if isinstance(prompt, Checklist):
        chosen = ",".join(str(index + 1) for index in sorted(prompt.selected))
        return f"Choose numbers, separated by commas [{chosen}]: "
    if isinstance(prompt, Confirm):
        return "[Y/n]: " if prompt.answer else "[y/N]: "
    return "> "


def _answer(prompt: Prompt, line: str) -> str | None:
    """Set the typed answer on the prompt; give why it can't be read, or None.

    An empty line keeps a choice's default; a text answer is taken as typed.
    """
    problem: str | None = None
    if isinstance(prompt, TextInput):
        prompt.text = line
    elif not line:
        pass
    elif isinstance(prompt, Select):
        if line.isdigit() and 1 <= int(line) <= len(prompt.choices):
            prompt.focus = int(line) - 1
        else:
            problem = f"Type a number from 1 to {len(prompt.choices)}."
    elif isinstance(prompt, Checklist):
        parts = [part.strip() for part in line.split(",") if part.strip()]
        if all(part.isdigit() and 1 <= int(part) <= len(prompt.choices) for part in parts):
            prompt.selected = {int(part) - 1 for part in parts}
        else:
            problem = f"Type numbers from 1 to {len(prompt.choices)}, separated by commas."
    elif isinstance(prompt, Confirm):
        if line.lower() in ("y", "yes", "n", "no"):
            prompt.answer = line.lower().startswith("y")
        else:
            problem = "Type y or n."
    return problem

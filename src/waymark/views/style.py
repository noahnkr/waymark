"""A small styling helper: color by role, symbols, bars, rules and wrapping.

Output carries color on a terminal, or when ``FORCE_COLOR`` asks for it, and never
when ``NO_COLOR`` is set. It falls back to ASCII symbols when the console can't
show the glyphs, as on a legacy Windows console, and wraps prose only on a
terminal, so piped output keeps whole lines.
"""

import re
import shutil
import sys
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TextIO

RESET = "\x1b[0m"

ACCENT = "accent"
OK = "ok"
ATTENTION = "attention"
DANGER = "danger"
MUTED = "muted"
STRONG = "strong"

_ROLES = {
    ACCENT: "36",  # cyan: section rules, headings, commands
    OK: "32",  # green: done and healthy
    ATTENTION: "33",  # yellow: what needs the human, warnings
    DANGER: "31",  # red: errors, blockers, critical findings
    MUTED: "2",  # dim: dates, owners, paths, records
    STRONG: "1",  # bold: names
}
"""The palette: each role and the one of the 16 standard colors it is drawn in."""

_LIST_MARKER = re.compile(r"(?:[-*•]|\d+\.)\s+")
"""The start of a list line, whose wrapped lines hang under its text."""

BAR_WIDTH = 10
RULE_WIDTH = 72
MIN_WIDTH = 60
MAX_WIDTH = 100

_GLYPHS = {
    "done": ("✓", "x"),
    "todo": ("○", "o"),
    "arrow": ("→", "->"),
    "human": ("◆", "*"),
    "error": ("✗", "X"),
    "warning": ("!", "!"),
    "bullet": ("•", "-"),
    "full": ("█", "#"),
    "empty": ("░", "."),
    "rule": ("─", "-"),
    "branch": ("├─", "|-"),
    "last": ("└─", "`-"),
    "stem": ("│", "|"),
    "milestone_done": ("◆", "*"),
    "milestone_open": ("◇", "o"),
    "star": ("✦", "*"),
    "current": ("●", "@"),
}


def _can_encode(stream: TextIO) -> bool:
    """Whether the stream's encoding can show every glyph the views use."""
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        "".join(glyph for glyph, _ in _GLYPHS.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def enable_escape_sequences() -> bool:
    """Turn on escape-sequence handling in a Windows console; False when it can't be."""
    enabled = True
    if sys.platform == "win32":
        import ctypes  # noqa: PLC0415 - only needed, and only importable, on Windows

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        enabled = bool(kernel.GetConsoleMode(handle, ctypes.byref(mode))) and bool(
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
        )
    return enabled


def _forced(environment: Mapping[str, str]) -> bool:
    """Whether ``FORCE_COLOR`` asks for color: set, and not empty or ``0``."""
    return environment.get("FORCE_COLOR", "") not in ("", "0")


@dataclass(frozen=True)
class Style:
    """How to draw: with or without color, with glyphs or ASCII, wrapped or not.

    ``width`` is the column prose wraps at, or ``None`` to leave lines whole.
    """

    color: bool = False
    unicode: bool = False
    width: int | None = None

    @classmethod
    def detect(cls, stream: TextIO, environment: Mapping[str, str]) -> "Style":
        """Choose a style for a stream from what it is and what the environment asks for.

        ``NO_COLOR`` wins over everything; ``FORCE_COLOR`` turns color on away from
        a terminal; otherwise only a terminal whose ``TERM`` isn't ``dumb`` gets
        color. Only a terminal gets a width: forcing color doesn't force wrapping.
        """
        terminal = bool(getattr(stream, "isatty", lambda: False)())
        if "NO_COLOR" in environment:
            color = False
        elif _forced(environment):
            if terminal:
                enable_escape_sequences()
            color = True
        else:
            color = terminal and environment.get("TERM") != "dumb" and enable_escape_sequences()
        width = None
        if terminal:
            columns = shutil.get_terminal_size().columns
            width = max(MIN_WIDTH, min(MAX_WIDTH, columns))
        return cls(color=color, unicode=_can_encode(stream), width=width)

    def paint(self, text: str, *roles: str) -> str:
        """Text drawn in the given roles, or unchanged when color is off."""
        if not self.color or not roles or not text:
            return text
        return f"\x1b[{';'.join(_ROLES[role] for role in roles)}m{text}{RESET}"

    def symbol(self, name: str) -> str:
        """A named symbol, as a glyph or as its ASCII stand-in."""
        glyph, plain = _GLYPHS[name]
        return glyph if self.unicode else plain

    def bar(self, done: int, total: int, width: int = BAR_WIDTH) -> str:
        """A progress bar for ``done`` out of ``total``."""
        filled = 0 if total <= 0 else min(width, done * width // total)
        if total > 0 and done >= total:
            filled = width
        bar = self.paint(self.symbol("full") * filled, OK) + self.paint(
            self.symbol("empty") * (width - filled), MUTED
        )
        return bar if self.unicode else f"[{bar}]"

    def rule(self, title: str, width: int = RULE_WIDTH) -> str:
        """A section rule with a title."""
        line = self.symbol("rule")
        head = f"{line * 2} {title} "
        return self.paint(head + line * max(2, width - len(head)), ACCENT)

    def wrap(self, text: str, indent: str = "") -> str:
        """Prose with ``indent`` before each line, wrapped at word boundaries to ``width``.

        Each line of ``text`` is a paragraph, wrapped on its own with its indent on
        every line; a list line (``- ``, ``* ``, ``• `` or ``1. ``) hangs its
        continuation lines under its text. A word longer than the width is left
        whole, and blank lines stay blank. With no width the paragraphs are only
        indented, one line each.
        """
        lines: list[str] = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                lines.append("")
                continue
            if self.width is None:
                lines.append(indent + paragraph)
                continue
            own = paragraph[: len(paragraph) - len(paragraph.lstrip())]
            marker = _LIST_MARKER.match(paragraph.lstrip())
            hang = " " * len(marker.group(0)) if marker else ""
            lines.extend(
                textwrap.wrap(
                    paragraph.strip(),
                    self.width,
                    initial_indent=indent + own,
                    subsequent_indent=indent + own + hang,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        return "\n".join(lines)

"""A small styling helper: color, symbols, progress bars and section rules.

Output is plain when it isn't going to a terminal or when ``NO_COLOR`` is set,
and falls back to ASCII symbols when the console can't show the glyphs, as on a
legacy Windows console.
"""

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TextIO

RESET = "\x1b[0m"
BOLD = "1"
DIM = "2"
RED = "31"
GREEN = "32"
YELLOW = "33"
CYAN = "36"

BAR_WIDTH = 10
RULE_WIDTH = 72

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
}


def _can_encode(stream: TextIO) -> bool:
    """Whether the stream's encoding can show every glyph the views use."""
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        "".join(glyph for glyph, _ in _GLYPHS.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _enable_windows_colors() -> bool:
    """Turn on escape-sequence handling in a Windows console; False when it can't be."""
    if sys.platform != "win32":
        return True
    import ctypes  # noqa: PLC0415 - only needed, and only importable, on Windows

    kernel = ctypes.windll.kernel32
    handle = kernel.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
        return False
    return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))


@dataclass(frozen=True)
class Style:
    """How to draw: with or without color, with glyphs or ASCII."""

    color: bool = False
    unicode: bool = False

    @classmethod
    def detect(cls, stream: TextIO, environment: Mapping[str, str]) -> "Style":
        """Choose a style for a stream from what it is and what the environment asks for."""
        terminal = bool(getattr(stream, "isatty", lambda: False)())
        wants_color = (
            terminal and "NO_COLOR" not in environment and environment.get("TERM") != "dumb"
        )
        return cls(color=wants_color and _enable_windows_colors(), unicode=_can_encode(stream))

    def paint(self, text: str, *codes: str) -> str:
        """Text in the given colors, or unchanged when color is off."""
        if not self.color or not codes or not text:
            return text
        return f"\x1b[{';'.join(codes)}m{text}{RESET}"

    def symbol(self, name: str) -> str:
        """A named symbol, as a glyph or as its ASCII stand-in."""
        glyph, plain = _GLYPHS[name]
        return glyph if self.unicode else plain

    def bar(self, done: int, total: int, width: int = BAR_WIDTH) -> str:
        """A progress bar for ``done`` out of ``total``."""
        filled = 0 if total <= 0 else min(width, done * width // total)
        if total > 0 and done >= total:
            filled = width
        bar = self.symbol("full") * filled + self.symbol("empty") * (width - filled)
        return bar if self.unicode else f"[{bar}]"

    def rule(self, title: str, width: int = RULE_WIDTH) -> str:
        """A section rule with a title."""
        line = self.symbol("rule")
        head = f"{line * 2} {title} "
        return self.paint(head + line * max(2, width - len(head)), BOLD)

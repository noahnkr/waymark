"""The terminal: key names from raw bytes on both platforms, and the line fallback."""

import io
from collections.abc import Iterator

import pytest

from waymark.services.setup import atlas_name_problem
from waymark.views.prompts import Checklist, Choice, Confirm, Outcome, Select, TextInput
from waymark.views.style import Style
from waymark.views.terminal import (
    RawModeUnavailable,
    RawTerminal,
    ask_by_line,
    posix_key,
    windows_key,
)

PLAIN = Style()
KINDS = (Choice("A project", "project"), Choice("An atlas", "atlas"))
TOOLS = (Choice("Claude Code", "claude-code", "found"), Choice("Other", "other"))


def chars(text: str) -> "Iterator[str]":
    return iter(text)


def from_windows(raw: str) -> str:
    rest = chars(raw[1:])
    return windows_key(raw[0], lambda: next(rest))


def from_posix(raw: str) -> str:
    rest = chars(raw[1:])
    return posix_key(raw[0], lambda: next(rest, None))


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("\xe0H", "up"),
        ("\xe0P", "down"),
        ("\x00K", "left"),
        ("\xe0M", "right"),
        (" ", "space"),
        ("\r", "enter"),
        ("\x08", "backspace"),
        ("\x1b", "escape"),
        ("\x03", "escape"),
        ("a", "a"),
    ],
)
def test_windows_keys(raw: str, key: str) -> None:
    assert from_windows(raw) == key


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("\x1b[A", "up"),
        ("\x1b[B", "down"),
        ("\x1b[C", "right"),
        ("\x1b[D", "left"),
        ("\x1bOA", "up"),
        (" ", "space"),
        ("\r", "enter"),
        ("\n", "enter"),
        ("\x7f", "backspace"),
        ("\x1b", "escape"),
        ("\x03", "escape"),
        ("2", "2"),
    ],
)
def test_posix_keys(raw: str, key: str) -> None:
    assert from_posix(raw) == key


def test_raw_mode_is_refused_away_from_a_terminal() -> None:
    with pytest.raises(RawModeUnavailable), RawTerminal(io.StringIO(), io.StringIO()):
        pass


def test_a_redraw_goes_back_over_the_last_drawing() -> None:
    out = io.StringIO()
    terminal = RawTerminal(io.StringIO(), out)
    terminal.draw(["one", "two", "three"])
    terminal.draw(["four", "five", "six"])
    written = out.getvalue()
    assert written.count("\x1b[2K") == 6
    assert "\x1b[2A" in written
    terminal.finish()
    terminal.draw(["seven"])
    assert out.getvalue().endswith("\r\x1b[2Kseven")


class Lines:
    """A fake ``input``: hands out typed lines, and keeps the prompts it was shown."""

    def __init__(self, *lines: str) -> None:
        self.lines = list(lines)
        self.hints: list[str] = []

    def __call__(self, hint: str) -> str:
        self.hints.append(hint)
        if not self.lines:
            raise EOFError
        return self.lines.pop(0)


def test_scenario_numbered_choices() -> None:
    """Requirement "Questions without raw mode": typing 2 picks the atlas, and its name is next."""
    shown: list[str] = []
    typed = Lines("2", "shop-platform")
    kind = Select("What is this repository?", KINDS)
    assert ask_by_line(kind, PLAIN, typed, shown.append) is Outcome.DONE
    assert shown[1:] == ["  1. A project", "  2. An atlas"]
    assert typed.hints[0] == "Choose 1-2 [1]: "
    assert kind.value == "atlas"
    name = TextInput("What is the atlas's name?", validate=atlas_name_problem)
    assert ask_by_line(name, PLAIN, typed, shown.append) is Outcome.DONE
    assert shown[-1] == "What is the atlas's name?"
    assert name.value == "shop-platform"


def test_line_fallback_keeps_the_defaults() -> None:
    kind = Select("What is this repository?", KINDS)
    assert ask_by_line(kind, PLAIN, Lines(""), lambda _: None) is Outcome.DONE
    assert kind.value == "project"
    tools = Checklist("Which agent tools?", TOOLS, selected=["claude-code"])
    typed = Lines("")
    assert ask_by_line(tools, PLAIN, typed, lambda _: None) is Outcome.DONE
    assert typed.hints == ["Choose numbers, separated by commas [1]: "]
    assert tools.value == ("claude-code",)
    ci = Confirm("Add the CI workflow?")
    assert ask_by_line(ci, PLAIN, Lines(""), lambda _: None) is Outcome.DONE
    assert ci.value is True


def test_line_fallback_validates_and_asks_again() -> None:
    shown: list[str] = []
    name = TextInput("What is the atlas's name?", validate=atlas_name_problem)
    typed = Lines("shop platform", "shop-platform")
    assert ask_by_line(name, PLAIN, typed, shown.append) is Outcome.DONE
    assert any("can't be an atlas name" in line for line in shown)
    assert name.value == "shop-platform"
    kind = Select("What is this repository?", KINDS)
    assert ask_by_line(kind, PLAIN, Lines("7", "1"), shown.append) is Outcome.DONE
    assert any("from 1 to 2" in line for line in shown)


def test_line_fallback_refuses_an_empty_tool_list() -> None:
    tools = Checklist("Which agent tools?", TOOLS, selected=[])
    shown: list[str] = []
    assert ask_by_line(tools, PLAIN, Lines("", "1"), shown.append) is Outcome.DONE
    assert any("at least one" in line for line in shown)
    assert tools.value == ("claude-code",)


def test_end_of_input_cancels() -> None:
    kind = Select("What is this repository?", KINDS)
    assert ask_by_line(kind, PLAIN, Lines(), lambda _: None) is Outcome.CANCELED

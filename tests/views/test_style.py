"""The styling helper: color, symbols, bars and rules, and when each is used."""

import io
import os

import pytest

from waymark.views.style import ACCENT, ATTENTION, DANGER, MUTED, OK, STRONG, Style


class Terminal(io.StringIO):
    """A stream that says it is a terminal, with a chosen encoding."""

    def __init__(self, encoding: str = "utf-8", terminal: bool = True) -> None:
        super().__init__()
        self._encoding = encoding
        self._terminal = terminal

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return self._encoding

    def isatty(self) -> bool:
        return self._terminal


def test_output_is_plain_when_piped() -> None:
    style = Style.detect(Terminal(terminal=False), {})
    assert not style.color
    assert style.paint("text", DANGER, STRONG) == "text"


def test_output_is_plain_when_no_color_is_set() -> None:
    assert not Style.detect(Terminal(), {"NO_COLOR": "1"}).color
    assert not Style.detect(Terminal(), {"NO_COLOR": ""}).color
    assert not Style.detect(Terminal(), {"TERM": "dumb"}).color


def test_color_wraps_text_in_escape_sequences() -> None:
    style = Style(color=True, unicode=True)
    assert style.paint("text", DANGER, STRONG) == "\x1b[31;1mtext\x1b[0m"
    assert style.paint("", DANGER) == ""
    assert style.paint("text") == "text"


def test_legacy_console_encoding_falls_back_to_ascii_symbols() -> None:
    for encoding in ("cp437", "cp1252", "ascii"):
        style = Style.detect(Terminal(encoding), {})
        assert not style.unicode
        drawn = style.symbol("done") + style.symbol("arrow") + style.bar(1, 2) + style.rule("T")
        drawn.encode("ascii")
    assert Style.detect(Terminal("utf-8"), {}).unicode
    assert not Style.detect(Terminal("no-such-encoding"), {}).unicode


def test_symbols_have_a_glyph_and_an_ascii_form() -> None:
    assert Style(unicode=True).symbol("done") == "✓"
    assert Style(unicode=False).symbol("done") == "x"
    assert Style(unicode=True).symbol("arrow") == "→"
    assert Style(unicode=False).symbol("arrow") == "->"


def test_progress_bar_fills_with_progress() -> None:
    plain = Style(unicode=False)
    assert plain.bar(0, 4) == "[..........]"
    assert plain.bar(1, 4) == "[##........]"
    assert plain.bar(4, 4) == "[##########]"
    assert plain.bar(0, 0) == "[..........]"
    assert plain.bar(9, 4) == "[##########]"
    assert Style(unicode=True).bar(1, 2) == "█████░░░░░"


def test_section_rule_carries_its_title() -> None:
    assert Style(unicode=False).rule("Changes", width=20) == "-- Changes ---------"
    assert Style(unicode=True).rule("Changes", width=20) == "── Changes ─────────"
    assert Style(color=True, unicode=False).rule("T", width=8).startswith("\x1b[36m-- T ")


def test_scenario_piped_output() -> None:
    """Requirement "Color on a terminal": piped output carries no color and no width."""
    style = Style.detect(Terminal(terminal=False), {})
    assert not style.color
    assert style.width is None


def test_scenario_forced_color() -> None:
    style = Style.detect(Terminal(terminal=False), {"FORCE_COLOR": "1"})
    assert style.color
    assert style.width is None
    for value in ("", "0"):
        assert not Style.detect(Terminal(terminal=False), {"FORCE_COLOR": value}).color


def test_scenario_no_color_wins() -> None:
    assert not Style.detect(Terminal(), {"FORCE_COLOR": "1", "NO_COLOR": "1"}).color
    assert not Style.detect(Terminal(terminal=False), {"FORCE_COLOR": "1", "NO_COLOR": ""}).color


def test_width_on_a_terminal_is_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    for columns, width in ((40, 60), (80, 80), (200, 100)):
        monkeypatch.setattr(
            "waymark.views.style.shutil.get_terminal_size",
            lambda columns=columns: os.terminal_size((columns, 24)),
        )
        assert Style.detect(Terminal(), {}).width == width


def test_every_role_has_a_standard_color() -> None:
    style = Style(color=True)
    codes = {ACCENT: "36", OK: "32", ATTENTION: "33", DANGER: "31", MUTED: "2", STRONG: "1"}
    for role, code in codes.items():
        assert style.paint("x", role) == f"\x1b[{code}mx\x1b[0m"


def test_new_glyphs_have_ascii_stand_ins() -> None:
    names = ("branch", "last", "stem", "milestone_done", "milestone_open", "star")
    for name in names:
        Style(unicode=False).symbol(name).encode("ascii")
        assert Style(unicode=True).symbol(name) != Style(unicode=False).symbol(name)


def test_wrap_at_width_sixty() -> None:
    paragraph = " ".join(["word"] * 40)
    wrapped = Style(width=60).wrap(paragraph, "    ").split("\n")
    assert len(wrapped) > 1
    assert all(len(line) <= 60 for line in wrapped)
    assert all(line.startswith("    word") for line in wrapped)
    assert " ".join(line.strip() for line in wrapped) == paragraph


def test_wrap_leaves_a_long_word_whole() -> None:
    long = "x" * 80
    assert Style(width=60).wrap(f"see {long} here", "  ").split("\n") == [
        "  see",
        f"  {long}",
        "  here",
    ]


def test_wrap_without_a_width_only_indents() -> None:
    text = " ".join(["word"] * 40) + "\n\n  nested line"
    assert Style().wrap(text, "  ") == "  " + " ".join(["word"] * 40) + "\n\n    nested line"


def test_wrap_hangs_a_list_line_under_its_text() -> None:
    """Design: list lines wrap with a hanging indent under their text."""
    item = "- " + " ".join(["word"] * 30)
    wrapped = Style(width=60).wrap(item, "  ").split("\n")
    assert wrapped[0].startswith("  - word")
    assert len(wrapped) > 1
    assert all(line.startswith("    word") for line in wrapped[1:])
    numbered = Style(width=60).wrap("12. " + " ".join(["word"] * 30), "").split("\n")
    assert all(line.startswith("    word") for line in numbered[1:])
    prose = Style(width=60).wrap(" ".join(["word"] * 30), "  ").split("\n")
    assert all(line.startswith("  word") for line in prose)

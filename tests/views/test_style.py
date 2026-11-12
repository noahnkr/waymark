"""The styling helper: color, symbols, bars and rules, and when each is used."""

import io

from waymark.views.style import BOLD, RED, Style


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
    assert style.paint("text", RED, BOLD) == "text"


def test_output_is_plain_when_no_color_is_set() -> None:
    assert not Style.detect(Terminal(), {"NO_COLOR": "1"}).color
    assert not Style.detect(Terminal(), {"NO_COLOR": ""}).color
    assert not Style.detect(Terminal(), {"TERM": "dumb"}).color


def test_color_wraps_text_in_escape_sequences() -> None:
    style = Style(color=True, unicode=True)
    assert style.paint("text", RED, BOLD) == "\x1b[31;1mtext\x1b[0m"
    assert style.paint("", RED) == ""
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
    assert Style(color=True, unicode=False).rule("T", width=8).startswith("\x1b[1m-- T ")

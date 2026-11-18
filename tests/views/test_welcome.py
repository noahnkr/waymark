"""The welcome screen: the star, its frames, its layout, and how it plays."""

from waymark.views.style import Style
from waymark.views.welcome import (
    CENTER,
    FRAMES,
    RING,
    SIZE,
    STAR,
    TAGLINE,
    play,
    screen,
    show_still,
    star_rows,
    text_lines,
)

GLYPHS = Style(unicode=True)


def test_the_star_is_eleven_rows_with_a_ring_around_a_gap() -> None:
    rows = star_rows(GLYPHS)
    assert len(rows) == SIZE
    assert all(len(row) == SIZE * 2 for row in rows)
    assert (CENTER, CENTER) not in STAR
    assert RING <= STAR
    middle = rows[CENTER]
    assert middle[CENTER * 2 : CENTER * 2 + 2] == "  "
    assert rows[0].strip() == "██"


def test_full_screen_at_100_columns_puts_the_text_beside_the_star() -> None:
    lines = screen(Style(unicode=True, width=100))
    text = text_lines(Style(unicode=True))
    assert len(lines) == max(SIZE, len(text))
    name = next(i for i, line in enumerate(lines) if "Waymark" in line)
    last = next(i for i, line in enumerate(lines) if "/wm-onboard" in line)
    assert (name + last) / 2 == CENTER
    assert lines[CENTER].startswith("█" * 10 + "  " + "█" * 10)
    assert any(TAGLINE in line for line in lines)
    assert all(len(line) <= 100 for line in lines)


def test_full_screen_at_80_columns_puts_the_text_under_the_star() -> None:
    lines = screen(Style(unicode=True, width=80))
    assert lines[SIZE] == ""
    assert lines[SIZE + 1] == "✦ Waymark"
    assert lines[SIZE + 2] == TAGLINE
    assert any("/wm-kickoff" in line for line in lines)
    assert all(len(line) <= 80 for line in lines)


def test_the_star_grows_in_through_four_frames() -> None:
    counts = [sum(row.count("█") for row in star_rows(GLYPHS, frame)) for frame in (1, 2, 3, 4)]
    assert counts == sorted(counts)
    assert len(set(counts)) == FRAMES
    assert counts[-1] == 2 * len(STAR)
    first = star_rows(GLYPHS, 1)
    assert first[0].strip() == ""
    assert first[CENTER].strip() != ""


def test_ascii_star_is_drawn_with_hashes() -> None:
    lines = screen(Style(width=100))
    star = "".join(line[: SIZE * 2] for line in lines)
    assert set(star) <= {"#", " "}
    assert "#" in star
    "\n".join(lines).encode("ascii")


def test_shown_text_lines_appear_one_by_one() -> None:
    style = Style(unicode=True, width=100)
    assert not any("Waymark" in line for line in screen(style, shown=0))
    assert any("Waymark" in line for line in screen(style, shown=1))
    assert not any(TAGLINE in line for line in screen(style, shown=1))


def test_twinkling_lights_the_tips_in_bold() -> None:
    style = Style(color=True, unicode=True, width=100)
    assert screen(style, lit=True) != screen(style, lit=False)
    plain = Style(unicode=True, width=100)
    assert screen(plain, lit=True) == screen(plain, lit=False)


class FakeScreen:
    """A raw terminal handing out keys; None in the queue is a pause with no key."""

    def __init__(self, keys: list[str | None]) -> None:
        self.keys = keys
        self.drawn: list[list[str]] = []
        self.finished = 0

    def draw(self, lines: list[str]) -> None:
        self.drawn.append(lines)

    def finish(self) -> None:
        self.finished += 1

    def key_waiting(self, timeout: float) -> bool:
        del timeout
        if not self.keys:
            return False
        if self.keys[0] is None:
            self.keys.pop(0)
            return False
        return True

    def read_key(self) -> str:
        key = self.keys.pop(0)
        assert key is not None
        return key


COLOR = Style(color=True, unicode=True, width=100)


def test_any_key_skips_to_the_full_screen_and_enter_starts() -> None:
    terminal = FakeScreen([None, "space", None, None, "enter"])
    assert play(terminal, COLOR) is True
    assert len(terminal.drawn) == 2 + 1 + 2 + 1
    assert terminal.drawn[2] == screen(COLOR)
    assert terminal.drawn[-1] == screen(COLOR)
    assert terminal.finished == 1


def test_it_twinkles_while_it_waits() -> None:
    frames = FRAMES + len(text_lines(COLOR))
    keys: list[str | None] = [None] * frames
    terminal = FakeScreen([*keys, None, None, "enter"])
    assert play(terminal, COLOR) is True
    waiting = terminal.drawn[frames + 1 : -1]
    assert waiting == [screen(COLOR, lit=True), screen(COLOR, lit=False)]


def test_escape_at_the_welcome_cancels() -> None:
    assert play(FakeScreen(["escape"]), COLOR) is False
    frames = FRAMES + len(text_lines(COLOR))
    assert play(FakeScreen([None] * frames + ["escape"]), COLOR) is False


def test_without_color_it_is_drawn_once_still() -> None:
    plain = Style(unicode=True, width=100)
    terminal = FakeScreen(["space", "enter"])
    assert play(terminal, plain) is True
    assert terminal.drawn == [screen(plain), screen(plain)]


def test_without_raw_mode_it_waits_for_enter_at_a_line() -> None:
    shown: list[str] = []
    assert show_still(Style(width=80), lambda _: "", shown.append) is True
    assert shown == screen(Style(width=80))

    def end_of_input(_: str) -> str:
        raise EOFError

    assert show_still(Style(width=80), end_of_input, shown.append) is False

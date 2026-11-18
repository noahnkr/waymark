"""The welcome screen ``wm init`` opens with on a terminal: the Waymark star and what comes next.

The star is 11 rows of pixels, two characters each, with a ring around a gap
at its center. It grows in through four frames, the text appears beside it (or
under it on a narrow terminal), and it twinkles until Enter: the four tips and
the cells around the ring switch between bold and normal. Without raw mode or
color it is drawn once, still.
"""

from collections.abc import Callable
from typing import Protocol

from waymark.views.style import ACCENT, MUTED, STRONG, Style
from waymark.views.terminal import read_line

SIZE = 11
CENTER = SIZE // 2
FRAMES = 4
FRAME_SECONDS = 0.12
LINE_SECONDS = 0.03
TWINKLE_SECONDS = 1.0
WIDE = 90
"""Below this many columns the text goes under the star instead of beside it."""
GAP = "    "
SHOULDER = 3
"""How far the rows beside the ring reach from the center, in pixels."""

TAGLINE = "Leave a trail your agents can follow."
CANCELED = "Setup canceled. Nothing was written."


def _star() -> frozenset[tuple[int, int]]:
    """The star's pixels as (row, column): four tapering arms around a ring with a gap."""
    widths = {0: 0, 1: 0, 2: 1, 3: 1, 4: 2}
    pixels = set()
    for offset, half in widths.items():
        for row in (offset, SIZE - 1 - offset):
            pixels |= {(row, CENTER + d) for d in range(-half, half + 1)}
            pixels |= {(CENTER + d, row) for d in range(-half, half + 1)}
    pixels |= {(row, col) for row in range(CENTER - 1, CENTER + 2) for col in range(SIZE)}
    pixels -= {(CENTER, CENTER)}
    pixels -= {
        (row, col) for row, col in pixels if abs(row - CENTER) == 1 and abs(col - CENTER) > SHOULDER
    }
    return frozenset(pixels)


STAR = _star()
RING = frozenset((CENTER + dr, CENTER + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
"""The eight pixels around the gap at the star's center."""
TWINKLE = frozenset(
    {(0, CENTER), (SIZE - 1, CENTER), (CENTER, 0), (CENTER, SIZE - 1)}
    | {(CENTER - 2, CENTER), (CENTER + 2, CENTER), (CENTER, CENTER - 2), (CENTER, CENTER + 2)}
)
"""The four tips, and the cells beside the ring along each arm."""


def _reach(pixel: tuple[int, int]) -> int:
    """How far a pixel is from the center, in steps along the arms."""
    return abs(pixel[0] - CENTER) + abs(pixel[1] - CENTER)


def _grown(frame: int) -> frozenset[tuple[int, int]]:
    """The pixels shown in a frame, 1 to ``FRAMES``; the last is the whole star."""
    if frame >= FRAMES:
        return STAR
    return frozenset(pixel for pixel in STAR if _reach(pixel) <= frame + 1)


def star_rows(style: Style, frame: int = FRAMES, *, lit: bool = False) -> list[str]:
    """The star's rows, two characters per pixel; ``lit`` draws the twinkling cells bold."""
    shown = _grown(frame)
    block = style.symbol("full")
    rows = []
    for row in range(SIZE):
        cells = []
        for col in range(SIZE):
            pixel = (row, col)
            if pixel not in shown:
                cells.append("  ")
            elif pixel in RING or (lit and pixel in TWINKLE):
                cells.append(style.paint(block * 2, ACCENT, STRONG))
            else:
                cells.append(style.paint(block * 2, ACCENT))
        rows.append("".join(cells))
    return rows


def text_lines(style: Style) -> list[str]:
    """The text beside the star: the name, the tagline, what init sets up, and what comes next."""
    bullet = style.symbol("bullet")
    return [
        style.paint(f"{style.symbol('star')} Waymark", STRONG),
        style.paint(TAGLINE, MUTED),
        "",
        "wm init sets up:",
        f"  {bullet} the record, in waymark/",
        f"  {bullet} skills, agents and hooks for your agent tools",
        f"  {bullet} the CI workflow, if you want it",
        "",
        "Then, in your agent tool:",
        f"  /wm-kickoff   {style.paint('draft the charter', MUTED)}",
        f"  /wm-onboard   {style.paint('take a first change through', MUTED)}",
    ]


def screen(
    style: Style, frame: int = FRAMES, *, shown: int | None = None, lit: bool = False
) -> list[str]:
    """The whole welcome screen: the star in a frame, with the first ``shown`` text lines.

    On a terminal at least ``WIDE`` columns wide the text sits beside the star,
    with the star's center row level with the middle of the text; on a narrower
    one, or with no width, the text goes under it.
    """
    star = star_rows(style, frame, lit=lit)
    text = text_lines(style)
    if shown is not None:
        text = text[:shown] + [""] * (len(text) - shown)
    if style.width is None or style.width < WIDE:
        return [line.rstrip() for line in (*star, "", *text)]
    top = max(0, len(text) // 2 - CENTER)
    star_top = max(0, CENTER - len(text) // 2)
    height = max(top + SIZE, star_top + len(text))
    plain_width = SIZE * 2
    lines = []
    for index in range(height):
        star_index = index - top
        text_index = index - star_top
        left = star[star_index] if 0 <= star_index < SIZE else ""
        left += " " * (plain_width - _visible(left))
        right = text[text_index] if 0 <= text_index < len(text) else ""
        lines.append(f"{left}{GAP}{right}".rstrip())
    return lines


def _visible(text: str) -> int:
    """The width text takes on screen, without its escape sequences."""
    width = 0
    escape = False
    for char in text:
        if char == "\x1b":
            escape = True
        elif escape:
            escape = char != "m"
        else:
            width += 1
    return width


class Screen(Protocol):
    """What the welcome screen needs of a raw terminal."""

    def draw(self, lines: list[str]) -> None: ...

    def finish(self) -> None: ...

    def read_key(self) -> str: ...

    def key_waiting(self, timeout: float) -> bool: ...


def play(terminal: Screen, style: Style) -> bool:
    """Show the welcome screen in raw mode until Enter; False when it is canceled.

    With color it grows in, then the text appears line by line, and any key skips
    to the whole screen; then it twinkles until Enter. Without color it is drawn
    once, still. Esc or Ctrl+C cancels.
    """
    if style.color:
        steps = [(frame, 0) for frame in range(1, FRAMES + 1)]
        steps += [(FRAMES, shown) for shown in range(1, len(text_lines(style)) + 1)]
        for frame, shown in steps:
            terminal.draw(screen(style, frame, shown=shown))
            pause = FRAME_SECONDS if shown == 0 else LINE_SECONDS
            if terminal.key_waiting(pause):
                if terminal.read_key() == "escape":
                    terminal.finish()
                    return False
                break
    lit = False
    terminal.draw(screen(style))
    while True:
        if not style.color or terminal.key_waiting(TWINKLE_SECONDS):
            key = terminal.read_key()
            if key in ("enter", "escape"):
                terminal.draw(screen(style))
                terminal.finish()
                return key == "enter"
        else:
            lit = not lit
            terminal.draw(screen(style, lit=lit))


def show_still(
    style: Style, read: Callable[[str], str] = read_line, write: Callable[[str], None] = print
) -> bool:
    """Draw the welcome screen once, still, and wait for Enter at a line; False when canceled."""
    for line in screen(style):
        write(line)
    try:
        read("Press Enter to start. ")
    except (EOFError, KeyboardInterrupt):
        return False
    return True

# Refresh view style: design

## Context

`views/style.py` holds `Style`: `detect` turns color on for a terminal unless `NO_COLOR` is set or `TERM` is `dumb`, enabling escape sequences in a Windows console through `ctypes`; `paint` wraps text in codes; `symbol` gives ten glyphs with ASCII stand-ins, chosen by whether the stream's encoding can show them all; `bar` and `rule` draw progress bars and section rules. Six codes are used: bold, dim, red, green, yellow, cyan. `views/render.py` draws every view's text from its payload with a `Style`; `cli.py` detects the style for standard output, and the hook's session start uses a plain `Style()`. Nothing wraps text: a paragraph is printed as one line, indented only on its first.

## Approach

1. **Palette by role.** `style.py` names roles instead of codes: `accent` (cyan: rules, headings, commands), `ok` (green), `attention` (yellow: needs the human, warnings), `danger` (red: errors, blockers, critical findings), `muted` (dim: dates, owners, paths, records), `strong` (bold: names). `render.py` paints by role only, so a view never names a color.
2. **Phases and bars.** A change's phase is colored by how far it has come: `proposed` to `planned` muted, `accepted` and `applying` accent, `applied` ok. A bar's filled part is ok and its empty part muted.
3. **Glyphs.** New symbols with ASCII stand-ins: `branch` `├─` (`|-`), `last` `└─` (`` `- ``), `stem` `│` (`|`), `milestone_done` `◆` (`*`), `milestone_open` `◇` (`o`), and `star` `✦` (`*`). The encoding check covers the whole set, as now.
4. **Views.**
   - `wm status`: rules in accent; each change's phase and bar colored; milestones with `◆`/`◇` per roadmap line count.
   - `wm show <change>`: items as a tree, records under each item on the stem, muted.
   - `wm show <milestone>`: roadmap lines with `◆` archived, `◇` active, a muted `○` planned.
   - `wm check`: findings grouped under each file's path, each with its line and code; the counts in attention or danger.
   - `wm doctor`: names padded to one column, messages wrapped.
5. **Wrapping.** `Style` gains `width: int | None`: on a terminal, `shutil.get_terminal_size()` clamped to 60–100; otherwise `None`. A `wrap(text, indent)` helper uses `textwrap` with `break_long_words=False` and the indent as both initial and subsequent indent, and returns the text unchanged when `width` is `None`. `render.py` wraps prose (proposal sections, summaries, messages) through it; list lines wrap with a hanging indent under their text.
6. **`FORCE_COLOR`.** `detect` reads `NO_COLOR` first (set: no color), then `FORCE_COLOR` (set and not empty or `0`: color), then the terminal and `TERM` test. Forcing color doesn't force wrapping: width comes only from a terminal.

A sketch of `wm status` after the change (color in brackets):

```
── Changes in flight ─────────────────────────────────────────  [accent]
  add-resources            planned    ██████░░░░ 6/9    → apply 2.1
  flatten-charter-rules    accepted   ░░░░░░░░░░ 0/3    ◆ accept (you)   [attention]

── Open milestones ───────────────────────────────────────────
  context-beyond-the-code  ◆ ◇ ◇   1/3 changes archived
```

and of a change's items in `wm show`:

```
Items
  ├─ ✓ 1.1 Read and check resources
  │    (ticked) 2026-11-18 by Noah Roberts                       [muted]
  ├─ ○ 1.2 Keep resources/ in git
  └─ ○ 1.3 wm new resource
```

## Decisions

### Decision: How many colors
- Status: decided
- Decided by: human
- Options: the 16 standard colors; 256 colors; truecolor
- Choice: the 16 standard colors
- Why: they follow the user's terminal theme, light or dark, and every terminal that shows color shows them

### Decision: FORCE_COLOR
- Status: decided
- Decided by: human
- Options: honor `FORCE_COLOR`; color only on a terminal
- Choice: honor it, with `NO_COLOR` winning
- Why: it is the common way to ask for color where the output is shown to a person but isn't a terminal; `NO_COLOR` is the stronger, opt-out convention

### Decision: Paint by role or by color
- Status: decided
- Decided by: planner
- Options: views name roles, and `style.py` maps roles to codes; views name codes, as now
- Choice: roles
- Why: one place decides the palette, and add-interactive-init's screens use the same roles

### Decision: Wrap to what width
- Status: decided
- Decided by: planner
- Options: the terminal's width, clamped to 60–100; the terminal's full width; no wrapping
- Choice: clamped to 60–100
- Why: prose past about 100 columns is hard to read on a wide terminal, and below 60 the indents leave too little room; piped output stays unwrapped so agents get whole lines

## Open questions

None.

## Risks and trade-offs

- Wrapping changes the text shown on a terminal, so a test comparing terminal output must fix the width; tests pass `Style(width=...)` instead of reading the real terminal.
- `◆`, `◇` and `✦` are missing from some fonts; they fall back only by encoding, not by font, so a font without them shows a box.
- `FORCE_COLOR` set in a CI log or an agent tool that doesn't render escape sequences shows them raw; that is what the variable asks for.

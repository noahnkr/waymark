# Tasks

## 1. Style

- [x] 1.1 Palette, glyphs, FORCE_COLOR and width in `Style`
  - **Criteria:**
    - `Style` paints by the roles accent, ok, attention, danger, muted and strong, mapped to cyan, green, yellow, red, dim and bold; no view in `render.py` names a color code
    - the glyphs `branch`, `last`, `stem`, `milestone_done`, `milestone_open` and `star` exist with ASCII stand-ins, and the encoding check covers every glyph
    - `detect` gives no color when `NO_COLOR` is set, color when `FORCE_COLOR` is set and not empty or `0`, and otherwise color only for a terminal whose `TERM` isn't `dumb`
    - `detect` sets `width` to the terminal's width clamped to 60–100 on a terminal, and `None` otherwise; `wrap` breaks at word boundaries, keeps the indent on every line, leaves a longer word whole, and returns the text unchanged when `width` is `None`
  - **Verify:**
    - `test_scenario_piped_output`, `test_scenario_forced_color`, `test_scenario_no_color_wins` and `test_scenario_json` in `tests/views/test_style.py` and `tests/test_views_cli.py`
    - tests for `wrap` at width 60 and with `None`, beside them

## 2. Views

- [x] 2.1 Status, inbox, check and doctor in the new style
  - **Criteria:**
    - `wm status` colors each phase (muted through `planned`, accent for `accepted` and `applying`, ok for `applied`) and each bar (ok filled, muted empty), and draws each milestone's roadmap as `◆`/`◇`
    - `wm check` groups findings under each file's path, and colors the counts by the worst finding
    - `wm inbox` and `wm doctor` wrap their prose through `wrap`, and `wm doctor` pads its check names to one column
    - with `Style()` (no color, no width), each view's text is unchanged except for the new glyphs and grouping
  - **Verify:**
    - view tests in `tests/test_views_cli.py` and `tests/services/test_doctor.py` with a fixed `Style(color=True, unicode=True, width=80)`, and the existing plain-output tests still pass
- [x] 2.2 Show views in the new style
  - **Criteria:**
    - `wm show <change>` draws items as a tree with `├─`, `└─` and `│`, records muted on the stem, and wraps the proposal's sections and each item's criteria
    - `wm show <milestone>` marks roadmap lines `◆` archived, `◇` active and a muted `○` planned
    - with an encoding of `cp437`, the same views use only the ASCII stand-ins and keep their layout
  - **Verify:**
    - `test_scenario_legacy_console`, `test_scenario_narrow_terminal` and `test_scenario_piped` in `tests/test_views_cli.py` or `tests/views/`
- [x] 2.3 Every criterion of an item hangs under its bullet
  - **Criteria:**
    - in `wm show <change>`, an item's Criteria and Verify that are a list start the list on the line after their label, so the first bullet wraps under its own text like the others
    - a Criteria or Verify of one line stays on its label's line
    - with `Style()` the lines are unchanged except that a list starts on the line after its label
  - **Verify:**
    - a test in `tests/test_views_cli.py` renders an item with two long criteria at width 80, and each criterion's wrapped lines hang under its text
- [x] 2.4 `wm check` wraps its messages on a terminal
  - **Criteria:**
    - on a terminal, each finding's message in `wm check` wraps to the width under the finding, with its wrapped lines hung under the message's start
    - with no width, each finding stays on one line, as written
  - **Verify:**
    - a test in `tests/test_views_cli.py` renders a long finding at width 80 and with `Style()`

## 3. Docs

- [x] 3.1 Docs for color and wrapping
  - **Criteria:**
    - `tools/docs.py` writes an "Environment" section into `docs/cli.md` naming `NO_COLOR`, `FORCE_COLOR` and wrapping on a terminal, and `docs/cli.md` is regenerated
    - the CHANGELOG's Unreleased section notes the new look, `FORCE_COLOR` and wrapping
  - **Verify:** `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass
- [x] 3.2 Docs name `wm check` among the views that wrap
  - **Criteria:**
    - the Environment section of `docs/cli.md` and the CHANGELOG's Unreleased entry name `wm check` among the views whose prose wraps on a terminal, and `docs/cli.md` is regenerated
  - **Verify:** `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- 2026-11-18 (accepted) fingerprint 991db444e526cae4 items 1.1, 2.1, 2.2, 3.1 by Noah Roberts
- 2026-11-18 (review) changes 1.1; covers 1.1, 2.1, 2.2, 3.1 by Noah Roberts: wrap() gives a wrapped list line no hanging indent: its continuation lines sit under the dash instead of under the text, as design step 5 requires, which shows in wm show's What changes and Non-goals
  - [warning] `src/waymark/views/style.py`: Style.wrap: a bulleted line's continuation lines are indented to the dash, not hung under the text as design step 5 says
- 2026-11-18 (review) pass covers 1.1, 2.1, 2.2, 3.1 by wm-reviewer: every criterion of items 1.1, 2.1, 2.2 and 3.1 holds and every terminal-output scenario is met; the earlier review's hanging-indent fix is in and tested; tests, lint, format, types, spelling and the docs check all pass
  - [suggestion] `src/waymark/views/style.py: Style.wrap`: with no width it still puts the indent before each line and turns whitespace-only lines into empty ones. Criterion 1.1 and the design say it "returns the text unchanged". Every view's plain output and the Piped scenario still hold, but the record and the code should say the same thing.
  - [suggestion] `src/waymark/views/render.py: _item_lines`: an item's first criterion is joined to its label ("Criteria: - ..."), so that line has no list marker and its wrapped lines go under "Criteria:" rather than under the bullet's text.
- 2026-11-18 (review) pass covers 2.3, 2.4, 3.2 by wm-reviewer: the criteria of 2.3, 2.4 and 3.2 hold, and wrapped criteria and wrapped check findings hang correctly at width 80 and with color; plain output keeps each line whole; the docs are regenerated and current; all tests, lint, format, types and spelling pass
  - [warning] `src/waymark/views/render.py:242`: a Criteria or Verify of a single bullet (like 2.4's own Verify) counts as a list and moves to the next line, but 2.3's second criterion says "of one line stays on its label's line". The two criteria can be read against each other here, and no test covers a one-bullet list.
  - [suggestion] `src/waymark/views/render.py:242`: only a "- " list is moved under its label, but `Style.wrap` also treats `* `, `•` and `1. ` lines as lists, so a numbered criteria list would still start on the label's line.
  - [suggestion] `tools/docs.py:128`: the Environment line is split into odd string pieces ("going " then "to a terminal is never wrapped."). The output is right, but the source reads awkwardly.
- 2026-11-18 (note) 1.1 by Noah Roberts: wrap(text, indent) with no width still puts the indent before each line, one line per paragraph, so piped output keeps its layout; the design's 'returns the text unchanged' is read as 'not wrapped'. Section rules are now drawn in accent, per the design's palette
- 2026-11-18 (reopened) 1.1 by Noah Roberts
- 2026-11-18 (note) 2.1 by Noah Roberts: In wm status a milestone's marks count its planned roadmap lines as open too, since they are on the roadmap and not archived; the bar now colors its filled part ok and its empty part muted in Style.bar
- 2026-11-18 (note) 2.2 by Noah Roberts: Prose is wrapped in the change, spec, milestone and exploration show views; a resource's sections are left unwrapped because they hold code and settings that wrapping would break. A roadmap line that is neither archived nor active (planned or missing) gets the muted open circle

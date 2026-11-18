# Tasks

## 1. Style

- [x] 1.1 Palette, glyphs, FORCE_COLOR and width in `Style`
  - Criteria:
    - `Style` paints by the roles accent, ok, attention, danger, muted and strong, mapped to cyan, green, yellow, red, dim and bold; no view in `render.py` names a color code
    - the glyphs `branch`, `last`, `stem`, `milestone_done`, `milestone_open` and `star` exist with ASCII stand-ins, and the encoding check covers every glyph
    - `detect` gives no color when `NO_COLOR` is set, color when `FORCE_COLOR` is set and not empty or `0`, and otherwise color only for a terminal whose `TERM` isn't `dumb`
    - `detect` sets `width` to the terminal's width clamped to 60–100 on a terminal, and `None` otherwise; `wrap` breaks at word boundaries, keeps the indent on every line, leaves a longer word whole, and returns the text unchanged when `width` is `None`
  - Verify:
    - `test_scenario_piped_output`, `test_scenario_forced_color`, `test_scenario_no_color_wins` and `test_scenario_json` in `tests/views/test_style.py` and `tests/test_views_cli.py`
    - tests for `wrap` at width 60 and with `None`, beside them
  - (note) 2026-11-18 by Noah Roberts: wrap(text, indent) with no width still puts the indent before each line, one line per paragraph, so piped output keeps its layout; the design's 'returns the text unchanged' is read as 'not wrapped'. Section rules are now drawn in accent, per the design's palette
  - (reopened) 2026-11-18 by Noah Roberts

## 2. Views

- [x] 2.1 Status, inbox, check and doctor in the new style
  - Criteria:
    - `wm status` colors each phase (muted through `planned`, accent for `accepted` and `applying`, ok for `applied`) and each bar (ok filled, muted empty), and draws each milestone's roadmap as `◆`/`◇`
    - `wm check` groups findings under each file's path, and colors the counts by the worst finding
    - `wm inbox` and `wm doctor` wrap their prose through `wrap`, and `wm doctor` pads its check names to one column
    - with `Style()` (no color, no width), each view's text is unchanged except for the new glyphs and grouping
  - Verify:
    - view tests in `tests/test_views_cli.py` and `tests/services/test_doctor.py` with a fixed `Style(color=True, unicode=True, width=80)`, and the existing plain-output tests still pass
  - (note) 2026-11-18 by Noah Roberts: In wm status a milestone's marks count its planned roadmap lines as open too, since they are on the roadmap and not archived; the bar now colors its filled part ok and its empty part muted in Style.bar
- [x] 2.2 Show views in the new style
  - Criteria:
    - `wm show <change>` draws items as a tree with `├─`, `└─` and `│`, records muted on the stem, and wraps the proposal's sections and each item's criteria
    - `wm show <milestone>` marks roadmap lines `◆` archived, `◇` active and a muted `○` planned
    - with an encoding of `cp437`, the same views use only the ASCII stand-ins and keep their layout
  - Verify:
    - `test_scenario_legacy_console`, `test_scenario_narrow_terminal` and `test_scenario_piped` in `tests/test_views_cli.py` or `tests/views/`
  - (note) 2026-11-18 by Noah Roberts: Prose is wrapped in the change, spec, milestone and exploration show views; a resource's sections are left unwrapped because they hold code and settings that wrapping would break. A roadmap line that is neither archived nor active (planned or missing) gets the muted open circle

## 3. Docs

- [x] 3.1 Docs for color and wrapping
  - Criteria:
    - `tools/docs.py` writes an "Environment" section into `docs/cli.md` naming `NO_COLOR`, `FORCE_COLOR` and wrapping on a terminal, and `docs/cli.md` is regenerated
    - the CHANGELOG's Unreleased section notes the new look, `FORCE_COLOR` and wrapping
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- (accepted) 2026-11-18 fingerprint 991db444e526cae4 items 1.1 2.1 2.2 3.1 by Noah Roberts
- (review) 2026-11-18 changes 1.1 covers 1.1 2.1 2.2 3.1 by Noah Roberts: wrap() gives a wrapped list line no hanging indent: its continuation lines sit under the dash instead of under the text, as design step 5 requires, which shows in wm show's What changes and Non-goals
  - warning `src/waymark/views/style.py`: Style.wrap: a bulleted line's continuation lines are indented to the dash, not hung under the text as design step 5 says
- (review) 2026-11-18 pass covers 1.1 2.1 2.2 3.1 by wm-reviewer: every criterion of items 1.1, 2.1, 2.2 and 3.1 holds and every terminal-output scenario is met; the earlier review's hanging-indent fix is in and tested; tests, lint, format, types, spelling and the docs check all pass
  - suggestion `src/waymark/views/style.py: Style.wrap`: with no width it still puts the indent before each line and turns whitespace-only lines into empty ones. Criterion 1.1 and the design say it "returns the text unchanged". Every view's plain output and the Piped scenario still hold, but the record and the code should say the same thing.
  - suggestion `src/waymark/views/render.py: _item_lines`: an item's first criterion is joined to its label ("Criteria: - ..."), so that line has no list marker and its wrapped lines go under "Criteria:" rather than under the bullet's text.

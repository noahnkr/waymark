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

- [ ] 3.1 Docs for color and wrapping
  - Criteria:
    - `tools/docs.py` writes an "Environment" section into `docs/cli.md` naming `NO_COLOR`, `FORCE_COLOR` and wrapping on a terminal, and `docs/cli.md` is regenerated
    - the CHANGELOG's Unreleased section notes the new look, `FORCE_COLOR` and wrapping
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- (accepted) 2026-11-18 fingerprint 991db444e526cae4 items 1.1 2.1 2.2 3.1 by Noah Roberts

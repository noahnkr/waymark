# Tasks

## 1. Building blocks

- [x] 1.1 Detection per adapter, and CI at init
  - Criteria:
    - `Adapter.detect(root)` exists, `False` by default; Claude Code's is `True` when `.claude/` or `CLAUDE.md` exists in the root
    - `init_project(..., ci=True)` writes `.github/workflows/waymark.yml` in the same transaction as the record, and `ci=False` writes what `wm init` wrote before
  - Verify:
    - tests for `detect` with and without `.claude/`, and for `init_project` with `ci=True` and `ci=False`, in `tests/services/test_setup.py`
- [x] 1.2 Prompts as state machines
  - Criteria:
    - `Select`, `Checklist`, `Confirm` and `TextInput` in `views/prompts.py` take key names and render lines with a `Style`, with no terminal access
    - `Checklist` refuses Enter with nothing selected, keeping the question open with a reason; `TextInput` refuses Enter while its validator gives a reason, showing it
    - `escape` from any prompt gives a canceled state
  - Verify:
    - tests feeding key sequences in a new `tests/views/test_prompts.py`, including `test_scenario_nothing_selected` and `test_scenario_invalid_atlas_name`
  - (note) 2026-11-18 by Noah Roberts: setup.atlas_name_problem() now holds the atlas-name rule that init_project refused with, so the TextInput can validate with the same rule; Select also takes a typed number, for the line fallback
- [x] 1.3 Raw keys, redraws and the line fallback
  - Criteria:
    - `views/terminal.py` reads keys in raw mode on Windows and POSIX, mapping arrows, Space, Enter, Backspace, Esc and Ctrl+C to key names, and restores the terminal mode and cursor in a `finally`
    - it redraws a prompt in place, and raises when raw mode can't be entered
    - the line fallback asks each question as numbered choices with `input()`, with the same defaults and validation
  - Verify:
    - tests of the key mapping from raw byte sequences of both platforms, and `test_scenario_numbered_choices` with a fake input, in a new `tests/views/test_terminal.py`
    - by hand: arrows, Space, Enter and Esc on Windows Terminal and one POSIX terminal, added to `docs/smoke-test.md`
  - (note) 2026-11-18 by Noah Roberts: The by-hand check of arrows, Space, Enter, Backspace and Esc on Windows Terminal and a POSIX terminal is in docs/smoke-test.md under Keys in a raw terminal; it runs at the release's smoke test, once 2.1 wires the questions into wm init. style.enable_escape_sequences is now public for the raw terminal
- [x] 1.4 The welcome screen
  - Criteria:
    - `views/welcome.py` draws the 11-row star with its ring, the name, the tagline "Leave a trail your agents can follow.", what `wm init` sets up and the skills to run next, the star's center row level with the middle of the text; below 90 columns, the text is under the star
    - on a terminal with color it grows in through four frames about 120 ms apart, any key skipping to the full screen, then twinkles until Enter; without raw mode or color it is drawn once, still
    - with ASCII glyphs, the star is drawn with `#`
  - Verify:
    - tests of the full screen at 100 and 80 columns, of the frames, and of the ASCII star, in a new `tests/views/test_welcome.py`
  - (note) 2026-11-18 by Noah Roberts: The star is drawn from the design's description, four tapering arms around a ring with a gap, not traced from the banner SVG, which has no pixel grid; its pixels use the full glyph, so ASCII draws it with #. Without color but with raw mode it is drawn once and waits for Enter; without raw mode show_still waits at a line

## 2. The flow

- [x] 2.1 Interactive `wm init`
  - Criteria:
    - `wm init` is interactive only when input and output are terminals and none of `--atlas`, `--tool`, `--yes` is given; `--yes` is a new flag
    - interactively, in a repository with no record, it shows the welcome screen, then the repository, tools and CI questions under the step indicator, then calls `init_project` with the answers and prints what it created and the next step
    - a tool question lists every adapter, selecting the detected ones, or all when none is detected, and marking detected ones "found"
    - Esc or Ctrl+C at any point prints `Setup canceled. Nothing was written.`, exits 1, and writes nothing
    - in a clone with a record, it shows the welcome screen, then sets up the machine with no question
  - Verify:
    - `test_scenario_project_with_claude_code_and_ci`, `test_scenario_atlas`, `test_scenario_tool_detected`, `test_scenario_canceled_at_the_tools`, `test_scenario_run_by_an_agent`, `test_scenario_yes_flag_on_a_terminal` and `test_scenario_clone_on_a_terminal`, with fake terminal streams and key sequences, in `tests/test_cli.py` or beside the setup tests
    - by hand: a full interactive `wm init` in a fresh repository on Windows, added to `docs/smoke-test.md`
  - (note) 2026-11-18 by Noah Roberts: The questions live in views/init_flow.py; cli.py runs them in raw mode and writes and prints only after raw mode ends, so the output keeps its line breaks. The step indicator adds a current glyph (● or @). docs/cli.md was regenerated here for --yes so the docs test stays green; item 3.1 still owns the docs. The by-hand Windows run is in docs/smoke-test.md's first step

## 3. Docs

- [x] 3.1 Docs for the interactive init
  - Criteria:
    - `docs/getting-started.md` shows the interactive `wm init` and says `--yes`, `--atlas` and `--tool` skip the questions
    - `docs/cli.md` is regenerated with `--yes`, and the CHANGELOG's Unreleased section notes the interactive init
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- (accepted) 2026-11-18 fingerprint e4640089b6be55b8 items 1.1 1.2 1.3 1.4 2.1 3.1 by Noah Roberts
- (accepted) 2026-11-18 fingerprint fb25b46e5fa16a1a items 1.1 1.2 1.3 1.4 2.1 3.1 by Noah Roberts
- (self-review) 2026-11-18 covers 1.1 1.2 1.3 1.4 2.1 3.1 by Noah Roberts: Every criterion of 1.1-3.1 holds and every setup scenario has a passing test; the full checks pass. The review found that on Windows Ctrl+C reaches the flow as KeyboardInterrupt, not a key, so it ended with a traceback; fixed in 6dc9328 with a test. The raw-mode key readers are checked by hand only at the smoke test
  - warning `src/waymark/views/terminal.py`: RawTerminal.draw: a redraw goes back over as many lines as it drew, so a line wider than the terminal wraps and the next redraw leaves part of it behind; no test covers it
  - warning `src/waymark/views/terminal.py`: the Windows and POSIX raw readers are tested only through their key mapping; reading real keys is checked by hand at the smoke test
  - suggestion `src/waymark/views/welcome.py`: text_lines: in a clone the welcome screen still says it sets up the CI workflow if you want it, though a clone asks nothing

# Add interactive init: design

## Context

`cli._init` passes `--atlas` and `--tool` to `setup.init_project`, which writes the settings, the charter, the folder keeps, every chosen tool's files and the `.gitignore` block in one transaction, defaulting to every adapter in `adapters.names()`; in a repository with a record it calls `_set_up_clone`, which refuses both flags. The CI workflow is written only by `wm ci` (`services/ci.py`, `stage_workflow`), which needs a pinned record. `Style` (from refresh-view-style) gives the palette roles, glyphs including `star`, and `width`. The charter allows only the standard library and only local git commands; constraint 6 keeps file writes in `record/`, so terminal input and output belong in `views/` and `cli.py`.

## Approach

1. **Prompts as state machines.** A new `views/prompts.py` holds `Select` (one of several), `Checklist` (any of several, at least one), `Confirm` (yes or no with a default) and `TextInput` (a line, with a validator). Each is pure: `handle(key) -> state` and `render(state, style) -> lines`, where keys are names (`up`, `down`, `space`, `enter`, `escape`, `backspace`, or a character). A `Checklist` refuses `enter` with nothing selected; a `TextInput` refuses `enter` while its validator returns a reason, showing it under the input.
2. **The terminal.** A new `views/terminal.py` reads one key at a time in raw mode, `msvcrt.getwch` on Windows (with the `\x00`/`\xe0` prefixes for arrows) and `termios`/`tty` on POSIX (with the `\x1b[A` sequences), mapping both to key names; Ctrl+C maps to `escape`. It redraws a prompt in place with cursor-up and erase-line sequences, hides the cursor while drawing, and restores the terminal mode and cursor in a `finally`. When raw mode can't be entered (`termios.error`, no console), it raises, and the caller falls back to line prompts: `input()` with numbered choices.
3. **The welcome screen.** A new `views/welcome.py` holds the 11-row star (two characters per pixel, a gap at the center for the ring) and its four growing frames, laid out with the text on the right, the star's center row level with the middle of the text. On a terminal narrower than 90 columns, the text goes under the star. The frames play about 120 ms apart, then the text appears line by line; any key skips to the full screen. While waiting for Enter it twinkles: the ring's neighbors and the four tips switch between bold and normal about once a second, read with a non-blocking key check (`msvcrt.kbhit`, or `select` on the POSIX stdin). Without raw mode or color, the screen is drawn once, still.
4. **The flow.** `cli._init` is interactive when `sys.stdin.isatty()` and `sys.stdout.isatty()` and none of `--atlas`, `--tool`, `--yes` is given. It shows the welcome screen; in a repository with a record it then calls `init_project` as today. Otherwise it asks the three questions under a step indicator (`◆ ─── ● ─── ○ ─── ○  Repository · Tools · CI · Done`), validates the atlas name with the same rule `init_project` uses, and calls `init_project(atlas, tools, ci=answer)`. A cancel prints `Setup cancelled. Nothing was written.` and exits 1; nothing has been written, because `init_project` runs only after the last answer.
5. **Detection.** `Adapter` gains `detect(root: Path) -> bool`, default `False`; Claude Code's returns whether `.claude/` or `CLAUDE.md` exists. The tool question selects the detected tools, or every tool when none is detected, and marks each detected one "found".
6. **CI at init.** `init_project` gains `ci: bool = False`; when true it stages the workflow with `ci.stage_workflow` in the same transaction, after the settings that pin the version, so the whole init stays one transaction.
7. **`--yes`.** A new flag on `wm init` that skips the welcome screen and the questions; with it, `wm init` behaves exactly as before this change.

## Decisions

### Decision: What init asks
- Status: decided
- Decided by: human
- Options: project or atlas, agent tools, and CI; those plus commit scopes and the review default; agent tools only
- Choice: project or atlas, agent tools, and CI
- Why: they are the choices made once at setup that today need a flag or a second command; the rest belongs to the charter and the settings, drafted later

### Decision: A tool list with one tool
- Status: decided
- Decided by: human
- Options: build the checklist now, listing every adapter; show a confirmation until a second adapter exists
- Choice: build the checklist now
- Why: a new adapter then appears with no change to `init`, and the one entry still shows whether the tool was found

### Decision: The welcome mark
- Status: decided
- Decided by: human
- Options: the banner's four-pointed star, 11 rows, animated; a smaller 7-row star; a cairn; a wordmark; the star with the banner's dotted trail
- Choice: the 11-row star, centered against the text, growing in and then twinkling
- Why: it is the mark the README's banner uses; the dotted trail didn't read well in a terminal

### Decision: Where the prompts come from
- Status: decided
- Decided by: planner
- Options: a small standard-library prompt module; a third-party prompt library
- Choice: a standard-library module
- Why: the charter allows only the standard library at runtime

### Decision: Defaults without questions
- Status: decided
- Decided by: planner
- Options: `--yes` and non-terminal runs behave as `wm init` does today (a project, every tool, no CI); they take the interactive defaults (detected tools, CI yes)
- Choice: as today
- Why: agents and scripts that run `wm init` see no change; the interactive defaults only start a question the human then answers

## Open questions

None.

## Risks and trade-offs

- Raw mode differs by platform and terminal; a terminal that misreports keys could leave a prompt stuck. Esc and Ctrl+C always cancel, the terminal mode is restored in a `finally`, and `--yes` is always there.
- The animation's redraws can flicker on slow terminals; it is short, skippable and plays once.
- The interactive path can't be fully tested without a terminal: the prompts and the flow are tested with key sequences and fake streams, and the raw-mode readers by hand on Windows, macOS and Linux, added to the smoke test.

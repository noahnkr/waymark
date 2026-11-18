# Refresh view style

- Owner: Noah Roberts

## Why

The views a person runs in a terminal (`wm status`, `wm inbox`, `wm check`, `wm show`, `wm doctor`) work, but they read flat: a few colors, ten glyphs, and long paragraphs printed as single lines that the terminal breaks mid-word. They are the face of Waymark for the human, who reads them between agent sessions, and the welcome screen that add-interactive-init brings needs the same palette and glyphs to build on.

Color itself needs no install: `wm` already writes the standard escape sequences, turns them on in the Windows console, and leaves them out when the output isn't a terminal. What it lacks is a way to force color where the output isn't a terminal but is shown to a person, which the common `FORCE_COLOR` variable gives.

## What changes

- One palette of the 16 standard colors, used by role in every view: an accent for section rules, headings and commands; green for done and healthy; yellow for what needs the human and for warnings; red for errors and blockers; dim for dates, owners and other detail; bold for names.
- More glyphs, each with an ASCII stand-in: tree lines for a change's items and their records, a filled and an open marker for a milestone's roadmap lines, and a star for the welcome screen.
- `wm status` colors each change's phase and progress bar; `wm show` draws a change's items as a tree and a milestone's roadmap with its markers; `wm check` groups findings by file; `wm doctor` aligns its results.
- On a terminal, prose in `wm show`, `wm inbox` and `wm doctor` is wrapped to the terminal's width, between 60 and 100 columns, with its indent kept. Output that isn't going to a terminal is not wrapped, so agents read whole lines as today.
- `FORCE_COLOR` turns color on when the output isn't a terminal; `NO_COLOR` still turns it off, and wins over `FORCE_COLOR`. JSON output never carries color.

## Non-goals

- No 256-color or truecolor; the 16 colors follow the user's terminal theme.
- No change to what any view says, or to the JSON payloads.
- No interactivity; that is add-interactive-init.
- No change to the hook's session-start status, which goes to the agent as plain text.

## Impact

- Specs: `terminal-output` (new)
- User-visible:
  - views use one 16-color palette, tree lines and roadmap markers, with ASCII stand-ins on consoles that can't show the glyphs
  - prose in `wm show`, `wm inbox` and `wm doctor` wraps to the terminal's width on a terminal
  - `FORCE_COLOR` forces color; `NO_COLOR` still wins
- Code: `views/style.py`, `views/render.py`, `cli.py` (style detection), the tests in `tests/views/` and the view tests, and the docs (`cli.md` for the environment variables, the CHANGELOG)

## Outcome

- Built: The terminal views use one 16-color palette by role, with tree lines for a change's items and filled and open marks for milestones, each with an ASCII stand-in. wm check groups findings by file and wm doctor aligns its checks. On a terminal, prose in wm show, wm inbox, wm check and wm doctor wraps to 60-100 columns, with list lines and criteria hanging under their text. FORCE_COLOR forces color and NO_COLOR wins. docs/cli.md has an Environment section.
- Differs: wm check wraps too, through items 2.3, 2.4 and 3.2, added after the first review and reviewed on their own. The self-review sent item 1.1 back for hanging list indents. The session-start hook's plain status shows milestone marks instead of a bar, against the proposal's non-goal. Resource sections in wm show are not wrapped. Left open: a one-bullet Criteria moves under its label, which item 2.3's wording can be read against; only '- ' lists move; wrap still indents with no width; and the tools/docs.py string split.

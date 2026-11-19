# Add interactive init

- **Owner:** Noah Roberts

## Why

`wm init` is the first thing a person runs, and it prints one line. It doesn't say what Waymark is, makes its choices silently (a project, every agent tool `wm` knows, no CI workflow), and leaves the atlas and the CI workflow to flags and a second command the person has to know about. A person runs it once per repository, in a terminal, before any agent session; it is the one command where asking questions fits. Every other command is mostly run by agents, and stays as it is.

## What changes

- On a terminal, with no `--atlas`, `--tool` or `--yes`, `wm init` in a repository without a record opens with a welcome screen: the Waymark star, drawn growing in, then the name, the tagline "Leave a trail your agents can follow.", what it sets up, and the skills to run next. The star twinkles until Enter.
- It then asks, one screen at a time, under a step indicator: whether the repository is a project or an atlas (and the atlas's name), which agent tools to set up, and whether to add the CI workflow. Then it writes what those answers ask for, as the flags would, and shows what it created and what to do next.
- The tool question lists every agent tool `wm` has an adapter for, so a new adapter appears in it with nothing else to change; a tool whose folder is found in the repository is selected to start with, and when none is found, all are.
- Esc or Ctrl+C at any question cancels: nothing is written, and `wm init` says so.
- In a clone that already has a record, `wm init` on a terminal shows the welcome screen, then sets up the machine from the record's settings, with no questions.
- Without a terminal on both input and output, or with `--atlas`, `--tool` or the new `--yes`, `wm init` asks nothing and does what it does today. Agents, `!` commands and CI see no change.
- Where the terminal can't be put in raw mode, the questions fall back to numbered choices typed at a line.

## Non-goals

- No other interactive command.
- No question about commit scopes, the review default or the charter; the charter is drafted with the wm-kickoff skill.
- No new agent tool adapters; the tool question shows the one there is, Claude Code.
- No change to what `wm init` writes for a given set of answers.

## Impact

- **Specs:** `setup` (added)
- **User-visible:**
  - `wm init` on a terminal shows a welcome screen and asks for the repository kind, the agent tools and the CI workflow
  - `wm init --yes` runs without questions; `--atlas` and `--tool` also skip them
  - canceling at a question writes nothing
- **Code:** a new terminal module and prompt module and welcome screen in `views/`, `cli.py` (`wm init` and `--yes`), `services/setup.py` (CI workflow at init), `services/ci.py`, `adapters/` (a detection hook per adapter), the tests, and the docs (`getting-started.md`, `cli.md` generated, the CHANGELOG)

## Outcome

- **Built:** On a terminal, wm init opens with a welcome screen (the Waymark star growing in and twinkling, the tagline, what it sets up and the skills to run next), then asks for the repository kind and atlas name, the agent tools (found ones pre-selected) and the CI workflow, and writes only after the last answer. Esc or Ctrl+C cancels with nothing written. Without raw mode the questions come as numbered choices. --yes, --atlas, --tool, or a piped input or output skip it all. Adapters gain detect(), and init_project can add the CI workflow.
- **Differs:** The proposal and delta were respelled to canceled, and the change was accepted again. The self-review found and fixed Ctrl+C arriving as KeyboardInterrupt on Windows. The star is drawn from the design's description, not traced from the banner SVG. docs/cli.md was regenerated in item 2.1. Left open: wide-line redraws, by-hand-only checks of the raw readers, and the clone's welcome text mentioning CI.

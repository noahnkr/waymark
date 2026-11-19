# Merge milestone files: design

## Context

- **Reading.** `record/milestones.py` reads `goal.md` with `parse_goal` (title, Goal, Done when, Non-goals) and `roadmap.md` with `parse_roadmap`, which takes every list line in the file as an entry. `Milestone` holds a `Goal` and a `Roadmap`, each with its own `Document`.
- **Loading.** `record/record.py` `_load_milestone` expects exactly `goal.md` and `roadmap.md`, reports any other file as `unexpected-file` and a missing one as `missing-file`. `Record.documents()` yields both documents. Archived milestones are only listed, as `ArchiveEntry`, and their files are not read.
- **Users.** `record/state.py` `milestone_state` counts the roadmap's entries; `views/payloads.py` `show_milestone` shows the goal's title and sections, and its JSON shape is documented in `docs/json.md`.
- **Writing.** `services/setup.py` `create_milestone` writes both files from the `goal.md` and `roadmap.md` templates. `services/lifecycle.py` `archive` runs `record/moves.py` `tick_roadmap_lines` on every document whose path ends in `/roadmap.md`, ticking each unchecked line that links into the archived folder, and `rewrite_links` on every document.
- **This record.** Two milestones: `record-format-and-skills`, active, and `archive/2026-11-15-lighter-workflow`. The exploration `lighter-workflow` links to the archived milestone's `goal.md` twice. Nothing else links to a milestone file.

## Approach

1. **Reading one file** (`record/milestones.py`).
   - `MILESTONE_FILE = "milestone.md"`. `parse_milestone(doc)` reads the title and the four sections, requires them in the order Goal, Done when, Non-goals, Roadmap, and returns a `Goal` and a `Roadmap` built from the same document.
   - Roadmap entries are the list lines between the `## Roadmap` heading and the end of that section, outside fenced code. `parse_goal`, `parse_roadmap`, `GOAL_FILE` and `ROADMAP_FILE` go, and so do the `goal.md` and `roadmap.md` templates.
2. **Loading** (`record/record.py`).
   - `_load_milestone` reads `milestone.md`. A `goal.md` or `roadmap.md` gives `milestone-file`, naming `milestone.md`; any other file stays `unexpected-file`; a missing `milestone.md` gives `missing-file`.
   - `Record.documents()` yields the milestone's document once.
   - Each archived milestone folder is listed with `files.entries`, and a `goal.md` or `roadmap.md` in it gives `milestone-file` too. Its `milestone.md` is not parsed, as archived milestones aren't today.
3. **Archiving a change** (`record/moves.py`, `services/lifecycle.py`).
   - `archive` runs `tick_roadmap_lines` on documents whose path ends in `/milestone.md`, and `tick_roadmap_lines` takes the line range of the `## Roadmap` section and ticks only lines inside it. `rewrite_links` still runs on every document, so a link in Done when to the change is rewritten but not ticked.
4. **Writing** (`services/setup.py`, `record/templates/`).
   - `create_milestone` writes `milestone.md` from a new `milestone.md` template with the four sections, their comments, and a good and a bad roadmap line in a comment.
5. **This record, by hand.**
   - `milestones/record-format-and-skills/` and `milestones/archive/2026-11-15-lighter-workflow/` each get a `milestone.md`: the goal file's text, then a `## Roadmap` section holding the roadmap file's lines without its title. The two old files are removed. No wording changes; links in the roadmap lines keep working, since the folder is the same.
   - The two links in `explorations/lighter-workflow.md` point at `milestone.md`.
6. **Skills and docs.** `wm-explore` says to draft the goal and list the likely changes under `## Roadmap` in `milestone.md`; `wm-archive` says to link the archived change in the milestone's Roadmap section. `docs/concepts.md` shows `milestones/<name>/milestone.md`, and the changelog says a milestone is one file. The generated docs are regenerated.

## Decisions

### Decision: How the file is laid out
- **Status:** decided
- **Decided by:** human
- **Options:**
  - Goal, Done when, Non-goals, then Roadmap;
  - Goal, then Roadmap, then Done when and Non-goals.
- **Choice:** Goal, Done when, Non-goals, Roadmap.
- **Why:** It reads top-down: why, when it is done, what it leaves out, then the changes.

### Decision: How the existing milestones move
- **Status:** decided
- **Decided by:** human
- **Options:**
  - by hand, once, in this change;
  - a `wm check --fix` step;
  - a new `wm` command.
- **Choice:** by hand, once.
- **Why:** There are two milestones and two links; a command or a fix would be code kept for one use.

### Decision: The archived milestone
- **Status:** decided
- **Decided by:** human
- **Options:**
  - merge it too, and rewrite the exploration's links;
  - leave it as written, and keep reading the two files for archived milestones.
- **Choice:** merge it too.
- **Why:** Only one layout is ever read, so the two-file reader can go entirely.

### Decision: Link rewriting for a moved file
- **Status:** decided
- **Decided by:** human
- **Options:**
  - leave it out;
  - build it in this change anyway.
- **Choice:** leave it out.
- **Why:** With the merge done by hand nothing moves a single file, and archiving and closing already rewrite links when they move a folder.

### Decision: One document, two views
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - keep `Goal` and `Roadmap`, both built from `milestone.md`;
  - one new `Milestone` type with the sections and the entries.
- **Choice:** keep `Goal` and `Roadmap`.
- **Why:** `milestone_state`, `show_milestone` and their JSON keep their shape, so the change stays in the reader, the loader and the writer.

### Decision: What an old file is reported as
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - a new code, `milestone-file`, naming `milestone.md`;
  - `old-layout`.
- **Choice:** `milestone-file`.
- **Why:** `old-layout` tells the human to run `wm update`, which can't merge the files.

## Open questions

None.

## Risks and trade-offs

- **No upgrade path.** A record with milestones in two files fails `wm check` after this change and has to be merged by hand. Only this repository uses Waymark, and its two milestones are merged here.
- **Roadmap entries depend on the heading.** A roadmap line written outside `## Roadmap`, such as under Done when, is not counted. The scenario "Roadmap ticked at archive" covers the boundary.
- **The JSON keeps `goal` and `title`.** `wm show <milestone> --json` keeps its shape, so nothing that reads it changes.

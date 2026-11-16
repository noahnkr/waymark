# Tasks

## 1. One milestone file

- [ ] 1.1 Read, load and write `milestone.md`, and merge this record's milestones
  - Criteria:
    - `parse_milestone` reads the title and the sections Goal, Done when, Non-goals and Roadmap, in that order, into a `Goal` and a `Roadmap` built from one document; roadmap entries are only the list lines inside `## Roadmap`, outside fenced code
    - `parse_goal`, `parse_roadmap`, `GOAL_FILE`, `ROADMAP_FILE` and the `goal.md` and `roadmap.md` templates are gone
    - a milestone folder, active or archived, holding `goal.md` or `roadmap.md` gives `milestone-file` naming `milestone.md`; another file gives `unexpected-file`; an active milestone without `milestone.md` gives `missing-file`
    - `Record.documents()` yields a milestone's document once
    - `wm new milestone` writes only `milestone.md`, from a new template with the four sections and a good and a bad roadmap line in a comment
    - `milestones/record-format-and-skills/` and `milestones/archive/2026-11-15-lighter-workflow/` each hold one `milestone.md`, merged by hand from their two files without changing wording, and the two links in `explorations/lighter-workflow.md` point at `milestone.md`
    - `wm show <milestone> --json` keeps its shape
  - Verify:
    - tests in `tests/record/test_artifacts.py`, `tests/record/test_project.py` and `tests/services/test_setup.py` for the scenarios "New milestone" and "Old milestone files"
    - the existing milestone tests in `tests/services/test_milestones.py`, `tests/record/test_state.py` and `tests/views/test_views.py`, moved to `milestone.md`, still pass
    - `wm check` and `wm status` here
- [ ] 1.2 Tick roadmap lines only inside the Roadmap section at archive
  - Criteria:
    - archiving a change ticks the unchecked lines linking into its folder inside the `## Roadmap` section of each `milestone.md`, and no line outside it
    - a link to the change elsewhere in `milestone.md` is still rewritten to the archived folder
  - Verify: a test in `tests/services/test_archive.py` for the scenario "Roadmap ticked at archive"

## 2. Skills and docs

- [ ] 2.1 Show the one file in the skills
  - Criteria:
    - `wm-explore` says to draft the goal and list the likely changes under `## Roadmap` in `milestone.md`
    - `wm-archive` says to link the archived change in the milestone's Roadmap section
  - Verify:
    - the assets tests in `tests/`
    - read both skills against the delta
- [ ] 2.2 Update the docs and the changelog
  - Criteria:
    - `docs/concepts.md` shows `milestones/<name>/milestone.md` and its four sections
    - the changelog says a milestone is one `milestone.md`, that `wm check` reports a `goal.md` or `roadmap.md`, and that such a record is merged by hand
    - the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

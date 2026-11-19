# Tasks

## 1. The log and the commands

- [x] 1.1 Add the milestone record kinds and read a milestone's Log
  - **Criteria:**
    - `(added)`, `(dropped)`, `(moved)`, `(proposed)` and `(archived)` render and parse in the shapes the "Milestone log" requirement gives, at a milestone level, and a malformed one is a parse error
    - `milestone.md` may end with a `## Log` section, whose records are read, and `wm check` reports a `## Log` that isn't the last section
    - a helper appends a record to a milestone's Log, creating the section at the end when there is none, with the file's line endings kept
    - `wm new milestone` still writes no `## Log`
  - **Verify:** tests in `tests/record/test_records.py` and `tests/record/` for the milestone file, for the scenarios "New milestone" and "Log not last"
- [x] 1.2 Change the roadmap with `wm roadmap add`, `drop` and `move`
  - **Criteria:**
    - each command edits the roadmap and appends its record to the Log in one write, keeping line endings, and takes `--by`
    - `add` refuses an invalid name or one already on the roadmap; `drop` needs `--reason` and refuses a change not on the roadmap or an active change that names the milestone; `move` takes `--after <change>` or `--first`, and refuses a change or target not on the roadmap
    - each refuses a milestone that isn't active, and writes nothing when it refuses
    - `docs/cli.md` is regenerated
  - **Verify:** tests in `tests/services/` and `tests/test_cli.py` for the scenarios "Line added", "Line moved", "Planned line dropped", "Active member not dropped" and "Log of a plan's changes"
- [x] 1.3 Write `(proposed)` and `(archived)`, and close a milestone only when every line is archived
  - **Criteria:**
    - `wm new change --milestone` writes `(proposed) <date> <change> by <who>` in the milestone's Log, in the same write as the proposal and the roadmap
    - archiving a change whose proposal names an active milestone writes `(archived) <date> <change> by <who>` in its Log
    - `wm close` refuses a milestone with a planned line, naming it and `wm roadmap drop`, and still refuses one with an active member
  - **Verify:** tests in `tests/services/test_setup.py`, `tests/services/test_archive.py` and `tests/services/test_lifecycle.py` for the scenarios "Planned roadmap line", "Change not on the roadmap", "Unknown milestone refused", "Member change archived", "Planned line keeps a milestone open" and "Every line archived"
- [x] 1.4 Refuse an agent's hand edits to roadmap lines and a milestone's Log
  - **Criteria:**
    - an agent's edit to an active milestone's `milestone.md` that adds, changes or removes a roadmap line or a Log record is refused, with a reason that names `wm roadmap`
    - an edit to the milestone's Goal, Done when or Non-goals is allowed
    - task lists are guarded as before
  - **Verify:** tests in `tests/record/test_evidence.py` and `tests/hooks/test_decide.py` for the scenarios "Agent adds a roadmap line by hand" and "Agent edits the goal"

## 2. Skills and docs

- [x] 2.1 Use `wm roadmap` in the skills, and describe it in the docs
  - **Criteria:**
    - `wm-explore` adds a new milestone's roadmap lines with `wm roadmap add`, and no skill says to write or edit a roadmap line by hand
    - `wm-archive` no longer says to link the archived change by hand, and says to change the roadmap with `wm roadmap` when the path changed
    - `docs/record.md` and `docs/concepts.md` describe `wm roadmap`, the milestone Log and its records, the guard on roadmap lines and the stricter `wm close`
    - the changelog's Unreleased section has the line, marked as a behavior change for `wm close`
    - the docs follow the `waymark-write-docs` skill
  - **Verify:** `uv run --no-sync pytest tests/adapters tests/test_docs.py`, codespell and `wm check`

## Log

- 2026-11-17 (accepted) fingerprint a282e6c537287e9c items 1.1, 1.2, 1.3, 1.4, 2.1 by Noah Roberts
- 2026-11-17 (review) pass covers 1.1, 1.2, 1.3, 1.4, 2.1 by wm-reviewer: every item's criteria and every delta scenario hold, and the tests, ruff, mypy, the docs-freshness test and wm check pass (codespell couldn't be run here); the warnings are an unparseable planned line that wm can't drop and a no-op move that still writes a record
  - [warning] `src/waymark/services/lifecycle.py:614`: a planned roadmap line that doesn't start with a valid change name (e.g. `- [ ] Paging, never proposed`, a form older milestones use) blocks `wm close`, `wm roadmap drop` refuses it because `entry_change` returns None, and the hook refuses an agent's hand edit to it — so the refusal's advice can't be followed and only a human hand edit unblocks the milestone; untested
  - [warning] `src/waymark/services/roadmap.py:801`: `move` writes a `(moved)` record even when the line doesn't change place (e.g. `--first` on the first line, or `--after` the line already before it); untested edge
  - [suggestion] `waymark/changes/add-milestone-log/tasks.md item 1.3`: its verification names `tests/services/test_lifecycle.py` for "Planned line keeps a milestone open" and "Every line archived", but those cases are in `tests/services/test_milestones.py::test_closing_moves_the_milestone_to_the_dated_archive`
  - [suggestion] `src/waymark/services/setup.py:876`: `wm new change --milestone` writes `(proposed)` with only the git user as its author and has no `--by`, unlike `wm roadmap` and `wm archive`
- 2026-11-17 (note) 1.3 by Noah Roberts: The close scenarios, Planned line keeps a milestone open and Every line archived, are tested in tests/services/test_milestones.py, where the wm close tests live, not in tests/services/test_lifecycle.py.

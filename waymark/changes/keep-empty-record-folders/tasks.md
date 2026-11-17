# Tasks

## 1. Record folders

- [x] 1.1 `wm init` writes a `.gitkeep` into each record folder when it creates a record
  - Criteria:
    - a new record's `specs/`, `changes/`, `changes/archive/`, `explorations/`, `milestones/` and `milestones/archive/` each hold an empty `.gitkeep`, written in the same transaction as the settings and the charter
    - a fresh clone of the committed record has all six folders
    - `wm init` in a clone that already has a record still writes nothing under `waymark/`, and `wm init` in a code repo is still refused
    - archiving the last active change leaves `changes/.gitkeep` in place, and `wm check` reports nothing about it
  - Verify:
    - `test_init_keeps_every_record_folder_in_git` in `tests/services/test_setup.py`, which commits the record and clones it
    - `test_archiving_the_last_change_keeps_the_changes_folder` in `tests/services/test_archive.py`
    - the existing clone and code-repo tests in `tests/services/test_setup.py` pass unchanged
- [x] 1.2 `wm update` writes any missing `.gitkeep`
  - Criteria:
    - on a record with none of the six `.gitkeep` files and no `changes/archive/`, `wm update` writes all six, prints `created: waymark/<folder>/.gitkeep` for each, and ends with the line asking to review the changes to `waymark/` and commit them
    - on a record that has all six, it writes none, prints nothing about them, and still ends with "Everything is up to date." when nothing else changed
    - this repository's record holds all six after running `wm update` here
  - Verify:
    - `test_update_adds_missing_record_folder_keeps` and `test_update_leaves_record_folder_keeps_alone` in `tests/adapters/test_integration.py`
    - `test_update_on_a_current_project_changes_nothing` passes unchanged
    - `git status` shows the new `waymark/**/.gitkeep` files after `wm update`

## 2. Docs

- [x] 2.1 Describe the `.gitkeep` files in the docs
  - Criteria:
    - `docs/record.md`'s layout notes that `wm init` writes a `.gitkeep` into each of the six folders so they are committed while empty, and that `wm update` adds a missing one
    - `docs/smoke-test.md`'s new-project step checks that the six folders hold a `.gitkeep`
  - Verify: `uv run --no-sync python -m tools.docs` leaves no generated file stale, and `uv run --no-sync pytest tests/test_docs.py` passes

## Log

- (accepted) 2026-11-16 fingerprint 5ff4406ce2f879c1 items 1.1 1.2 2.1 by Noah Roberts

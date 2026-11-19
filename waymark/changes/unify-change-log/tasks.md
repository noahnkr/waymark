# Tasks

## 1. Item records in the Log

- [x] 1.1 Read item records from the Log, naming their item
  - **Build:** planner
  - **Criteria:**
    - `(blocked)`, `(gap)`, `(note)` and `(reopened)` take one item number after the kind, and `(resolved)` an optional one; a record naming an item the change doesn't have is reported as `unknown-item`
    - the Log accepts item records, and each item's records, notes, blocker and spec gap are gathered from the Log by the item named, in order; records still under an item are read as before
    - a `(resolved)` for one item clears only that item's blocker, and change-level queries skip records that name an item
  - **Verify:**
    - tests in `tests/record/test_tasks_records.py` for the scenarios Resolved item keeps its blocker and Records for two items, and for a `(resolved)` with an item not counted as resolving the review
    - `uv run --no-sync pytest tests/record tests/services` and `wm check`
- [x] 1.2 Write item records into the Log
  - **Build:** planner
  - **Criteria:**
    - `wm block`, `wm gap`, `wm note`, `wm reopen`, `wm resolve <change> <item>` and an implementer's ending append their record to the Log with the item number, creating the section when needed, and write nothing under the item
    - the tests for the scenarios Blocked item, Note on an unticked item, Note on a ticked item, Implementer partly done, Record added and Acceptance in the Log pass
  - **Verify:**
    - `uv run --no-sync pytest tests/services tests/test_lifecycle_cli.py tests/test_agent_cli.py`
    - `wm check`
- [x] 1.3 Show each item's records with it
  - **Build:** planner
  - **Criteria:**
    - `wm show <change>` shows each item's records under the item in text and in JSON, gathered from the Log, and the Log as written; the implement pack shows an item's notes and resolutions as before
    - a JSON schema whose fields change has its version raised
  - **Verify:**
    - tests in `tests/views/test_views.py` and `tests/services/test_agent_interface.py` for the scenarios Blocker shown with its item and Note in the implementer's pack
    - `uv run --no-sync pytest tests/views tests/services`

## 2. The record moved

- [x] 2.1 Move the archive's item records into their Logs with an uncommitted script
  - **Build:** planner
  - **Criteria:**
    - a Python script run from the scratchpad, never committed, moves every record under an item of an archived change into that change's Log, with the item number after the kind, after the last Log record dated on or before it, item records of one day in item order; it creates a Log where there is none and changes nothing else
    - every archived change shows the same records per item with `wm show <change>` as before the script, and `wm check` is healthy
  - **Verify:**
    - `wm show <change> --json` on each archived change before and after, compared per item
    - `wm check`
- [ ] 2.2 Report a record under an item
  - **Build:** planner
  - **Criteria:**
    - a record under an item of an active change is no longer read, and `wm check` reports it as `misplaced-record`, saying it belongs in the Log
    - an item record in the Log is no longer reported as misplaced
    - the tests for the scenarios Record under an item and Implementer writes a note by hand pass
  - **Verify:**
    - tests in `tests/record/test_tasks_records.py` and `tests/hooks/test_decide.py`
    - `uv run --no-sync pytest` and `wm check`

## 3. Skills and docs

- [ ] 3.1 Update the skills, the agent definitions, the docs and the CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `wm-apply` and the `wm-implementer` and `wm-reviewer` agents say an item's records are in the change's Log, naming the item
    - `docs/record.md` and `docs/concepts.md` describe one Log holding every record, following the `waymark-write-docs` skill; `docs/cli.md` and `docs/json.md` are regenerated with `uv run --no-sync python -m tools.docs`
    - `CHANGELOG.md` has the User-visible lines under `## [Unreleased]`
  - **Verify:**
    - `uv run --no-sync pytest tests/test_skills.py tests/adapters`
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks: `pytest`, `ruff format --check .`, `ruff check .`, `mypy`, `codespell`

## Log

- 2026-11-18 (accepted) fingerprint 3bcdcf537052f64f items 1.1, 1.2, 1.3, 2.1, 2.2, 3.1 by Noah Roberts

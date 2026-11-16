# Tasks

## 1. Records, layout and migration

- [x] 1.1 Define every record kind once in `record/records.py`
  - Criteria: `RecordKind`, `Record`, and a table per kind give its argument grammar, whether it has text, whether it is a change-level or item record, and its shape for messages; `render` and `parse` round-trip every kind, with the arguments first and `by <who>` running to `: ` or the end of the line; findings render and parse as ``- <severity> `<place>`: <text>``, with a place that holds `: `; `who_for` gives `--by`, else the git user, else None, and refuses a value with `: `
  - Verify: `uv run --no-sync pytest tests/record/test_records.py`, with tests named after the requirements "One record shape", "Who wrote a record" and "Findings name their place in backticks"
- [x] 1.2 Read item records and the Log
  - Criteria: `record/tasks.py` reads item records into `Item.records` and the `## Log` section into `Tasks.log` through `records.parse`; `Item.blocked` and `Item.spec_gap` follow from the last `(blocked)` or `(gap)` record with no `(resolved)` after it; the acceptance and the sync come from the latest `(accepted)` and `(synced)` records; `wm check` reports `old-record-format`, `log-section-last`, `misplaced-record` and a malformed record with its expected shape
  - Verify: tests in `tests/record/` for the scenario "Malformed record", a resolved blocker, the latest acceptance counting, and an archived format 2 change
- [x] 1.3 Write format 2 records from every command, and add `wm note`
  - Criteria: `wm accept`, `wm sync` and `wm archive --override` append `(accepted)`, `(synced)` and `(override)` to the Log and leave the proposal alone; re-acceptance appends a new `(accepted)`; `wm block`, `wm gap`, `wm note`, `wm reopen` and `wm resolve` write item records, and `wm resolve` keeps what it resolves; `wm review` and `wm verdict` write to the Log with backticked findings; every writing command takes `--by`; `wm note` refuses a ticked item and an unaccepted change; `wm pr` lists the review records and the override
  - Verify: tests in `tests/services/test_lifecycle.py` and `tests/test_cli.py` for the scenarios "Blocked item", "Explicit author", "Resolved item keeps its blocker", "Note on an unticked item", "Note on a ticked item", "Acceptance in the Log", "Accepted again", "Record added", "Self-review with a finding", "Place with a line number", "Not reviewed" and "Overridden"
- [x] 1.4 Hash the standard layout, migrate every change to format 2 and drop format 1
  - Criteria: `record/layout.py` `standard_layout` fixes list markers, blank lines around headings, trailing spaces, the final line break and record lines, outside fenced code and comments, keeping line endings, and is idempotent; every fingerprint part is hashed after it, and no old hash is kept; the format 1 to 2 migration reads the files with its own patterns and does what the requirement "Record format 2" lists for active and archived changes, keeping each acceptance's digest and dating undated lines from the file's last commit or today; `RECORD_FORMAT` is 2; every format 1 reader and writer is removed (the `## Review` section, the old labels, `Accepted:` and `Synced:` lines, the `review:` tag, the format switch), and the tests move to format 2, with format 1 only in the migration's tests; afterwards the planner runs `wm update` on this repository and the human accepts this change again
  - Verify: tests in `tests/record/test_layout.py`, `tests/record/test_fingerprint.py` and `tests/services/test_migrations.py` for the scenarios "Accepted change migrated", "Archived change migrated" and "Item added", and idempotence; then `wm update`, `wm check` and `wm status` here
  - (reopened) 2026-11-16 by Noah Roberts
- [x] 1.5 Add `wm check --fix`
  - Criteria: `--fix` opens the record for writing, runs `standard_layout` over the charter, specs, active changes, explorations and milestones, never archived changes, and writes every changed file or none; it refuses, writing nothing, when the fix would change any acceptance state, record or tick; it names each fixed file and its kinds of fix, or says there was nothing to fix, then reports the check, failing when an error remains
  - Verify: tests in `tests/services/test_check.py` and `tests/test_cli.py` for the scenarios "Layout fixed", "Fenced code left alone", "Nothing to fix", "Error that can't be fixed", "Accepted change fixed" and "Older record format"
- [x] 1.6 Guard the records in the hooks and write agent endings `by` the agent
  - Criteria: evidence is every tick and every record in an active change's task list; an implementer's edit to any file in the record is refused with a reason that names `wm note` and `RESULT:`; `only_adds_notes` is gone; an implementer's ending is recorded `by wm-implementer`, with `partial` writing a `(note)`, and a reviewer's `by wm-reviewer`, from a final message or a handed-back report
  - Verify: tests in `tests/hooks/test_decide.py` and `tests/record/test_evidence.py` for the scenarios "Implementer writes a note by hand", "Reviewer's verdict", "Implementer done in the foreground", "Implementer partly done", "Implementer in the background" and "Reviewer in the background"
- [x] 1.7 Show item records and the Log in `wm show`
  - Criteria: `wm show <change>` in text and `--json` gives each item's records and the change's Log, in place of the review records; the `show.change` schema version is raised and `docs/json.md` regenerated
  - Verify: tests in `tests/views/`, and `uv run --no-sync python -m tools.docs --check`

## 2. Skills, charter and docs

- [x] 2.1 Rewrite the skills and agent definitions for records and the Log
  - Criteria: `wm-apply` and `wm-update` name the item records, `wm note`, `--by` and the Log; `wm-propose` and `wm-archive` no longer name `Accepted:` or `Blocked:` lines; `wm-implementer` writes notes with `wm note` or its ending and never edits the record; `wm-reviewer` matches the finding format; the planner runs `wm update` to regenerate the rendered files
  - Verify: `uv run --no-sync pytest tests/adapters`; read each changed skill once through as the planner would
  - (reopened) 2026-11-16 by Noah Roberts
- [x] 2.2 Update the charter and the docs
  - Criteria: the charter's careful-writes constraint names the exception for `wm check --fix`, which changes layout and never wording; concepts (the records, the Log, the glossary), getting started, the smoke test, architecture and the README describe format 2 and `--fix`; the generated docs are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync codespell` and `wm check`
  - (reopened) 2026-11-16 by Noah Roberts

## Log

- (accepted) 2026-11-15 fingerprint 3fc3fc068d5f1065 items 1.1 1.2 1.3 1.4 1.5 1.6 1.7 2.1 2.2 by Noah Roberts
- (accepted) 2026-11-15 fingerprint 09e0abc398f6fe46 items 1.1 1.2 1.3 1.4 1.5 1.6 1.7 2.1 2.2 by Noah Roberts
- (accepted) 2026-11-16 fingerprint 17a58d5e20a36cdc items 1.1 1.2 1.3 1.4 1.5 1.6 1.7 2.1 2.2 by Noah Roberts
- (review) 2026-11-16 changes 1.4 2.1 2.2 by wm-reviewer: 1.4: move tests/record/test_fingerprint.py:160-183 to format 2 records (a `(note)` and `(blocked)` under items, a `(self-review)` in `## Log`); 2.1: name `--by` in the wm-update skill and run `wm update` to regenerate the rendered copy; 2.2: describe `wm check --fix` in docs/getting-started.md and add it to docs/smoke-test.md
  - critical `tests/record/test_fingerprint.py:160-183`: `test_ticks_blockers_review_records_and_notes_keep_acceptance` still adds format 1 lines (` - Note:`, ` - Blocked:`, a `## Review` section); these are now `old-record-format` lines, not records, so the test no longer checks that records keep acceptance, and item 1.4 says format 1 appears only in the migration's tests
  - critical `src/waymark/assets/skills/wm-update/SKILL.md`: never names `--by` (no match in the file); item 2.1 says wm-apply and wm-update both name the item records, `wm note`, `--by` and the Log
  - critical `docs/getting-started.md`: not changed by this change and never mentions `wm check --fix` (its commands table lists only `wm check`); docs/smoke-test.md updates the review line to the Log but has no `--fix` step either; item 2.2 says getting started and the smoke test describe format 2 and `--fix`
  - warning `src/waymark/services/lifecycle.py:118`: without `--by`, `accept` takes `git.user_name` straight, skipping `records.check_who`; a git name holding `: ` would write an `(accepted)` record that no longer parses, while every other command falls back to no name
  - warning `src/waymark/services/pr.py:47-69`: `wm pr` shows only the last review record and its findings (with the place not in backticks), not every review record as item 1.3 says ("lists the review records")
  - warning `src/waymark/hooks/decide.py:299-302`: an implementer may run `wm note` on any change and item, not only its own; nothing checks the change and item it was started with
  - suggestion `src/waymark/hooks/decide.py:52-55`: `_EVIDENCE_COMMANDS`, quoted when an edit that touches a record or tick is refused, doesn't list `wm note`
  - suggestion `src/waymark/views/render.py:220-225`: the text `wm show` prints an `(accepted)` record as `(accepted) <date> 1.1 1.2 by <who>`, without `fingerprint`/`items`, and the JSON leaves out the fingerprint, so it reads unlike the record in the file
  - suggestion `tests/services/test_lifecycle_format2.py, tests/record/test_tasks_format2.py`: the `_format2` suffix is left over from when two formats existed side by side; now that only format 2 exists, these tests could join test_lifecycle.py and test_tasks.py, the files item 1.3's verification names

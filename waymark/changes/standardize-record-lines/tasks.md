# Tasks

## 1. Records, layout and migration

- [x] 1.1 Define every record kind once in `record/records.py`
  - Criteria: `RecordKind`, `Record`, and a table per kind give its argument grammar, whether it has text, whether it is a change-level or item record, and its shape for messages; `render` and `parse` round-trip every kind, with the arguments first and `by <who>` running to `: ` or the end of the line; findings render and parse as ``- <severity> `<place>`: <text>``, with a place that holds `: `; `who_for` gives `--by`, else the git user, else None, and refuses a value with `: `
  - Verify: `uv run --no-sync pytest tests/record/test_records.py`, with tests named after the requirements "One record shape", "Who wrote a record" and "Findings name their place in backticks"
- [x] 1.2 Read item records and the Log by the record's format
  - Criteria: `record/tasks.py` reads item records into `Item.records` and the `## Log` section into `Tasks.log` through `records.parse`; `Item.blocked` and `Item.spec_gap` follow from the last `(blocked)` or `(gap)` record with no `(resolved)` after it; the acceptance and the sync come from the latest `(accepted)` and `(synced)` records; a format 1 record and every archived change are read with the format 1 readers; in an active change, `wm check` reports `old-record-format`, `log-section-last`, `misplaced-record` and a malformed record with its expected shape
  - Verify: tests in `tests/record/` for the scenarios "Malformed record" and "Older acceptance line", a resolved blocker, the latest acceptance counting, and an archived format 1 change read as written
- [x] 1.3 Write format 2 records from every command, and add `wm note`
  - Criteria: `wm accept`, `wm sync` and `wm archive --override` append `(accepted)`, `(synced)` and `(override)` to the Log and leave the proposal alone; re-acceptance appends a new `(accepted)`; `wm block`, `wm gap`, `wm note`, `wm reopen` and `wm resolve` write item records, and `wm resolve` keeps what it resolves; `wm review` and `wm verdict` write to the Log with backticked findings; every writing command takes `--by`; `wm note` refuses a ticked item and an unaccepted change; `wm pr` lists the review records and the override
  - Verify: tests in `tests/services/test_lifecycle.py` and `tests/test_cli.py` for the scenarios "Blocked item", "Explicit author", "Resolved item keeps its blocker", "Note on an unticked item", "Note on a ticked item", "Acceptance in the Log", "Accepted again", "Record added", "Self-review with a finding", "Place with a line number", "Not reviewed" and "Overridden"
- [ ] 1.4 Hash the standard layout, migrate to format 2 and raise the record format
  - Criteria: `record/layout.py` `standard_layout` fixes list markers, blank lines around headings, trailing spaces, the final line break and record lines, outside fenced code and comments, keeping line endings, and is idempotent; every fingerprint part is hashed after it, with the old hash kept as `legacy_fingerprint`; the format 1 to 2 migration does what the requirement "Record format 2" lists, re-stamps an acceptance that `legacy_fingerprint` shows valid, dates undated lines from the file's last commit or today, and leaves archived changes alone; `RECORD_FORMAT` is 2; the commands' format 1 writing path is removed and the tests that wrote format 1 write format 2, while tests of reading format 1 stay; afterwards the planner runs `wm update` on this repository and this change is still accepted
  - Verify: tests in `tests/record/test_layout.py`, `tests/record/test_fingerprint.py` and `tests/services/test_migrations.py` for the scenarios "Accepted change migrated", "Archived change left as written" and "Item added", and idempotence; then `wm update` and `wm status` here
- [ ] 1.5 Add `wm check --fix`
  - Criteria: `--fix` opens the record for writing, runs `standard_layout` over the charter, specs, active changes, explorations and milestones, never archived changes, and writes every changed file or none; it refuses, writing nothing, when the fix would change any acceptance state, record or tick; it names each fixed file and its kinds of fix, or says there was nothing to fix, then reports the check, failing when an error remains
  - Verify: tests in `tests/services/test_check.py` and `tests/test_cli.py` for the scenarios "Layout fixed", "Fenced code left alone", "Nothing to fix", "Error that can't be fixed", "Accepted change fixed" and "Older record format"
- [ ] 1.6 Guard the records in the hooks and write agent endings `by` the agent
  - Criteria: evidence is every tick and every record in an active change's task list; an implementer's edit to any file in the record is refused with a reason that names `wm note` and `RESULT:`; `only_adds_notes` is gone; an implementer's ending is recorded `by wm-implementer`, with `partial` writing a `(note)`, and a reviewer's `by wm-reviewer`, from a final message or a handed-back report
  - Verify: tests in `tests/hooks/test_decide.py` and `tests/record/test_evidence.py` for the scenarios "Implementer writes a note by hand", "Reviewer's verdict", "Implementer done in the foreground", "Implementer partly done", "Implementer in the background" and "Reviewer in the background"
- [ ] 1.7 Show item records and the Log in `wm show`
  - Criteria: `wm show <change>` in text and `--json` gives each item's records and the change's Log, in place of the review records; the `show.change` schema version is raised and `docs/json.md` regenerated
  - Verify: tests in `tests/views/`, and `uv run --no-sync python -m tools.docs --check`

## 2. Skills, charter and docs

- [ ] 2.1 Rewrite the skills and agent definitions for records and the Log
  - Criteria: `wm-apply` and `wm-update` name the item records, `wm note`, `--by` and the Log; `wm-propose` and `wm-archive` no longer name `Accepted:` or `Blocked:` lines; `wm-implementer` writes notes with `wm note` or its ending and never edits the record; `wm-reviewer` matches the finding format; the planner runs `wm update` to regenerate the rendered files
  - Verify: `uv run --no-sync pytest tests/adapters`; read each changed skill once through as the planner would
- [ ] 2.2 Update the charter and the docs
  - Criteria: the charter's careful-writes constraint names the exception for `wm check --fix`, which changes layout and never wording; concepts (the records, the Log, the glossary), getting started, the smoke test, architecture and the README describe format 2 and `--fix`; the generated docs are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync codespell` and `wm check`

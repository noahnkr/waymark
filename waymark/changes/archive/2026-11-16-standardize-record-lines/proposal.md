# Standardize record lines

Owner: Noah Roberts
Review: independent

## Why

What `wm` writes into the record comes in four shapes today:

- `Key: value` lines in the proposal (`Accepted:`, `Synced:`, `Review override:`);
- labeled sub-lines under an item (`Blocked:`, `Spec gap:`, `Note:`), which look like the human's `Criteria:` and `Verify:` and carry no date;
- `(lowercase)` records, which put the date in different places: `(review) DATE verdict:`, `(self-review) DATE:`, `(reopened) DATE`;
- a `## Review` section that holds only part of a change's evidence.

A reader can't tell at a glance what a human wrote and what `wm` wrote. Each format is defined twice, as a string in `services/lifecycle.py` and as a pattern in `record/tasks.py`. `wm resolve` deletes the `Blocked:` line it resolves, so the record loses what blocked the item. Nothing tidies a record that drifts from its standard layout.

This is the first change on the `record-format-and-skills` milestone. The later changes there build on the record shape it sets and on `wm check --fix`.

## What changes

- **One convention.** What a human writes is a `Capital-Label:` line. What `wm` writes is a record: `(kind) YYYY-MM-DD [<args>] [by <who>]: <text>`: the date straight after the kind, then the kind's arguments, then who wrote it, which runs to the `: ` or the end of the line. `<who>` is the git user for a command the human or planner runs, and `wm-implementer` or `wm-reviewer` for an agent's ending; `--by` sets it explicitly.
- **Item records.** Under an item, `wm` writes `(blocked)`, `(gap)`, `(note)`, `(reopened)` and `(resolved)` records. Resolving an item adds a `(resolved)` record and keeps what it resolved, so the record keeps its history. A new `wm note <change> <item> "<text>"` writes a note, and agents no longer edit the task list by hand: every record comes from `wm`.
- **A `## Log` section** at the end of the task list replaces `## Review` and holds every change-level record: `(accepted) 2026-11-15 fingerprint <digest> items 1.1 1.2 by <who>`, `(synced)`, `(override)`, `(self-review)`, `(review)` and `(resolved)`. The proposal holds only what the human writes.
- **Findings** put the place in backticks: ``- critical `src/a.py:12`: <text>``, so a place that contains ": " is read correctly.
- **One definition per record kind.** A single module renders and parses every record, and every command that writes one goes through it.
- **`wm check --fix`** rewrites the record into its standard layout: the records `wm` owns, and the layout of human-written text (list markers, blank lines around headings, trailing spaces, the final newline). It never changes wording. It reports what it changed. The charter's careful-writes constraint gains this exception, for a fix the human asks for.
- **Record format 2, and nothing older.** `wm update` migrates every change, active and archived, to the new shapes and moves its acceptance, sync and override into the Log. Old per-item reviews become `(note)` records, and old `review:` tags go. `wm` then reads only format 2, so the format 1 readers, the old acceptance line without items and the old fingerprint are removed (the human chose this). An acceptance keeps its fingerprint, so an active change is accepted again after the migration.
- **Skills, agent definitions and docs** name the new records and the Log.

## Non-goals

- The human-written formats: proposal lines as a list, the glossary, criteria as nested lists, the `Build:` sub-line, delta headings. They are the next change on the milestone, `tidy-authored-notes`, which extends `--fix`.
- Rewriting the wording of anything a human wrote.
- Dating the tick on an item. A tick stays a checkbox.

## Impact

- New spec `records`: the record shape, the item records, the Log section, keeping resolved records, findings with a backticked place, and the format 2 migration.
- New spec `formatting`: what `wm check --fix` rewrites, what it leaves alone, and what it reports.
- Spec `acceptance`: the acceptance is an `(accepted)` record in the Log, with its items; the requirements that name the acceptance line are modified, and "Acceptance without an item list" is removed.
- Spec `review`: the review records and the override are written in the Log, with backticked places in findings; the requirements "Review recorded in the task list" and "Archive needs the change's review" are modified, and "No review tag on items" is removed.
- Spec `agent-results`: the reviewer's verdict is written in the Log, with `by wm-reviewer`; the scenario that names the `## Review` section is modified.
- **Behavior change for every user, for the changelog:**
  - the record format goes to 2, `wm update` migrates every change, archived ones too, and active changes are accepted again;
  - the `## Review` section becomes `## Log`, and the acceptance, sync and override move there from the proposal;
  - `Blocked:`, `Spec gap:` and `Note:` become dated `(blocked)`, `(gap)` and `(note)` records, and `wm resolve` keeps them;
  - every record carries a date and who wrote it, and the writing commands take `--by`;
  - `wm note` is new, and an implementer may no longer add note lines to the task list by hand;
  - `wm check --fix` is new;
  - the charter constraint on careful writes gains an exception for `--fix`.
- Code: `record/` (a records module, tasks, proposal, evidence, fingerprint, state), `services/` (lifecycle, check, migrations, pr), `hooks/decide.py` (the evidence guard and agent endings), `views/` and `cli.py`.
- Assets: `wm-apply`, `wm-update`, `wm-propose`, `wm-archive`, and the `wm-implementer` and `wm-reviewer` definitions.
- Docs: concepts, getting started, the smoke test, architecture, the README and the regenerated CLI and JSON references; the charter's constraints.

## Outcome

Every line wm writes is now a dated record, (kind) DATE [args] [by WHO]: text. Item records sit under their item, and change-level records sit in a ## Log that replaced ## Review. A records module defines each kind once. wm note, --by on every writing command, and wm check --fix (layout only, with the fingerprint taken over the standard layout) are new. Record format 2 is the only format wm reads. wm update migrated every change, archived ones too, and active changes were accepted again. Beyond the proposal, (synced) carries the re-stamped fingerprint so the Log stays append-only, implementers may run wm note, and --fix adds no blank line after headings. The first independent review asked for changes to 1.4, 2.1 and 2.2; the second passed. Item 2.3, added afterwards, closed that review's warnings and was checked by a separate read-only review, since wm doesn't ask for a new review when an item is added after a pass.

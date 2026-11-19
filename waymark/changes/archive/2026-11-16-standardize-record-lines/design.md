# Standardize record lines: design

## Context

- **Where records are defined.**
  - Each format is a regex in `record/tasks.py` (`_REVIEW`, `_SELF_REVIEW`, `_REOPENED`, `_RESOLVED`, `_CHANGE_REVIEW`, `_FINDING`, the labels `Blocked`, `Spec gap` and `Note` in `_LABELED`).
  - The same format is also an f-string in `services/lifecycle.py` (`self_review`, `verdict`, `reopen`, `resolve`, `_add_stopper`, `add_note`).
- **Where they are written.**
  - `record/edits.py` writes them: `edit_item` adds and removes lines under an item, `add_review` appends to the `## Review` section, and `set_fact` writes `Accepted:` and `Synced:` under the proposal's title.
  - `wm archive --override` appends `Review override: <reason>` to the outcome.
- **Who reads them.**
  - `record/state.py` derives the acceptance from `proposal.acceptance` and the sync from `proposal.synced`, and a blocked item from `item.blocked`.
  - `record/evidence.py` lists the evidence lines the hook guards: ticks, item records, the whole Review section, and the proposal's `Accepted|Synced|Review override` lines.
  - `services/pr.py`, `services/context.py` and `views/` (`payloads.py`, `render.py`, `schemas.py`) show the records.
- **The fingerprint** (`record/fingerprint.py`) hashes:
  - the proposal minus its acceptance and outcome;
  - the review level, the design and the deltas, the living text of modified and removed requirements, and each named item's definition.

  Only line endings are normalized, so any whitespace edit withdraws acceptance.
- **Implementer notes.** `hooks/decide.py` lets an implementer edit its change's `tasks.md` only to add `  - Note:` lines (`only_adds_notes`). A `partial` ending writes a note through `lifecycle.add_note`.
- **Migrations.** `services/migrations.py` runs one-step migrations from `wm update`, each applied with its new format number in one transaction. `RECORD_FORMAT` is 1 and there are no migrations yet.
- **`wm check`.** `services/check.py` collects problems from the parsers and the state. `cli.py`'s `_check` prints them, and it has no writing mode.

## Approach

1. **A records module, `record/records.py`.**
   - A `RecordKind` enum: `accepted`, `synced`, `override`, `self-review`, `review`, `resolved`, `reopened`, `blocked`, `gap` and `note`.
   - A `Record` dataclass: kind, date, args, who, text.
   - A table per kind gives:
     - its argument grammar: none; a verdict and item numbers; `fingerprint <hex16> items <n>...` for an acceptance; or an optional `fingerprint <hex16>` for a sync;
     - whether it has text;
     - whether it is a change-level record or an item record;
     - the shape shown in error messages.
   - `render(record) -> str` and `parse(line) -> Record | ParseError` are the only places a record's text is built or read. `parse` reads the arguments by the kind's grammar, then an optional `by <who>` that runs to `: ` or the end of the line, then the text.
   - Findings live here too: `render_finding` and `parse_finding`, with the place in backticks.
   - `who_for(root, by)` gives `--by`, else the git user, else None.
2. **Task list.**
   - `record/tasks.py` reads item records and the `## Log` section through `records.parse`, into `Item.records` and `Tasks.log`.
   - `Item.blocked` and `Item.spec_gap` become properties derived from the records: the last `(blocked)` or `(gap)` record with no `(resolved)` after it.
   - `wm` reads only format 2 (the human chose this). The format 1 readers go: the `## Review` section, the `Blocked:`, `Spec gap:` and `Note:` labels, the old record regexes, the `review:` tag and the per-change format switch. Writing commands already refuse a record in an older format and name `wm update`.
   - An old-form line gives `old-record-format` ("run `wm update`"). A `## Log` that isn't last gives `log-section-last`, and a change-level record under an item gives `misplaced-record`.
3. **Proposal.**
   - `record/proposal.py` stops reading `Accepted:` and `Synced:`. The acceptance and the sync come from the latest `(accepted)` and `(synced)` records in the Log.
   - An `Accepted:`, `Synced:` or `Review override:` line left in a proposal gives `old-record-format`.
   - `Change.acceptance` and `Change.synced` become the one place `state.py` asks.
4. **Writes.** `record/edits.py`:
   - `edit_item` gains `add_records` and loses `remove`, since records are never removed;
   - `append_log(tasks, record, findings)` replaces `add_review` and creates `## Log` when needed;
   - `set_fact` is no longer used for `Accepted:` or `Synced:`.

   In `services/lifecycle.py`, every command builds a `Record` and renders it, and each takes `by: str | None`:
   - `accept`, `sync` and `archive --override` append to the Log;
   - `sync` stamps the acceptance again for the merged specs without rewriting the `(accepted)` record. It writes the new fingerprint on its own record, `(synced) <date> fingerprint <digest> by <who>`, and a `(synced)` record after the latest `(accepted)` supplies the fingerprint that acceptance is checked against. A `(synced)` record without a fingerprint, from the migration, changes nothing;
   - `wm block` and `wm gap` add item records;
   - `wm resolve` adds `(resolved)` and keeps what it resolves;
   - the new `note` command, `wm note <change> <item> "<text>"`, writes a `(note)`.
5. **Layout, `record/layout.py`.**
   - `standard_layout(text) -> tuple[str, tuple[Fix, ...]]` is a pure function. It works outside fenced code and comments, and keeps line endings.
   - It does:
     - list markers `*` and `+` to `-`;
     - one blank line before each heading, and at most one after it (none is added, so requirements and scenarios keep their text directly under the heading, the human chose this);
     - no trailing spaces;
     - one final line break;
     - each line that `records.parse` reads re-rendered with `records.render`.
   - It is idempotent: running it twice gives the same text.
6. **Fingerprint.** Every part is hashed after `standard_layout`, so a fix can't change a fingerprint. No old hash is kept.
7. **`wm check --fix`** (`services/check.py`, `cli.py`).
   - It opens the record for writing, so the version-pin and format refusals apply.
   - It runs `standard_layout` over the charter, the specs, every file of each active change, the explorations and the milestones, and stages the changed files in one `Transaction`.
   - Before committing, it compares each change's acceptance state and its records and ticks before and after the fix. A difference is a fault in `wm`, so the fix is refused and nothing is written.
   - It prints each fixed file with its kinds of fix, then the usual check.
8. **Migration from format 1 to 2** (`services/format_two.py`, run by `services/migrations.py` with `RECORD_FORMAT = 2`). It reads the files as text with its own few patterns, since `wm` no longer parses format 1. For every change, active and archived:
   - `Blocked:`, `Spec gap:` and `Note:` lines become `(blocked)`, `(gap)` and `(note)` records;
   - a review record under an item becomes a `(note)` record that keeps its date and says what it was, such as `(note) 2026-01-19: review pass: boundary covered`, and a `review:` tag on an item goes;
   - the `## Review` section becomes `## Log`, with its findings re-rendered;
   - the proposal's `Accepted:`, `Synced:` and `Review override:` lines, and a `Review override:` paragraph at the end of an archived outcome, move to the top of the Log.

   The `(accepted)` record keeps the old line's date, who and digest, and names every item when the old line named none. The digest no longer matches the new fingerprint, so an active change is accepted again after the migration.

   A line without a date takes the date of `git log -1 --format=%cs -- <file>`, or today when the file isn't committed. The migration doesn't run `standard_layout` over human text; `wm check --fix` does that when the human asks.
9. **Hooks** (`hooks/decide.py`, `record/evidence.py`).
   - Evidence is every tick and every line `records.parse` reads in an active change's task list.
   - An implementer's edit to any file under the record is refused, with a reason that names `wm note` and the `RESULT:` line. `only_adds_notes` goes.
   - Agent endings call lifecycle with `by="wm-implementer"` or `by="wm-reviewer"`. A `partial` result writes `(note) … by wm-implementer: partial: <note>`.
10. **Views and PR.**
    - `wm show` (text and JSON) gives each item's records and the change's Log in place of the review records.
    - The `show.change` schema version goes up.
    - `wm pr` lists the review records and an `(override)` from the Log.
11. **Assets and docs.**
    - Skills: `wm-apply` and `wm-update` name the records, `wm note` and the Log; `wm-propose` and `wm-archive` stop naming `Accepted:`.
    - `wm-implementer` writes notes with `wm note` and never edits the record. `wm-reviewer` is unchanged apart from the finding format it sees.
    - The charter's careful-writes constraint gains the `--fix` exception.
    - Docs: concepts (the records and the Log), getting started, the smoke test, architecture, the README, and the regenerated CLI and JSON references.

## Decisions

### Decision: How a fix keeps acceptance
- **Options:**
  - hash every fingerprint part after `standard_layout`;
  - have `--fix` skip accepted changes and the specs they modify;
  - have `--fix` write a fresh acceptance for an accepted change.
- **Choice:** hash after `standard_layout`.
- **Why:** Layout then can't withdraw acceptance, whoever changes it, so a hand edit that only fixes layout keeps acceptance too. Skipping accepted changes leaves the files that matter most untidy. Writing an acceptance for the human breaks "only the human accepts".

### Decision: What stays of format 1
- **Options:**
  - migrate every change, archived ones too, and read only format 2;
  - drop only the old hash, and keep reading archived changes in format 1;
  - keep format 1 readers and the old hash, migrating only active changes.
- **Choice:** migrate every change and read only format 2 (the human chose it).
- **Why:** One format means one parser, no format switch, no old hash and no requirements kept only for history. Git keeps the files as they were. The cost is one re-acceptance of each active change, and old per-item reviews kept as notes rather than as reviews.

### Decision: Where the record shapes live
- **Options:**
  - one module with a table per kind;
  - a regex and an f-string per kind, as now.
- **Choice:** one module with a table per kind.
- **Why:** Each shape is defined once, the error messages are built from the same table, and a later kind is one table row.

### Decision: The date of a migrated line that had none
- **Options:**
  - the date of the last commit that touched the file;
  - the day of the migration;
  - a placeholder such as `undated`.
- **Choice:** the last commit that touched the file, or the day of the migration when it isn't committed.
- **Why:** That date is the nearest true one `wm` can find, and it keeps every record dated, so the parser needs no special case.

### Decision: Implementer access to the record
- **Options:**
  - no edits to the record at all, with notes through `wm note`;
  - hand edits that add a `(note)` record, checked by the hook.
- **Choice:** no edits (the human chose it).
- **Why:** Every record then comes from `wm`, and the hook's one exception goes away.

### Decision: Re-acceptance
- **Options:**
  - append a new `(accepted)` record, where the latest counts;
  - replace the record.
- **Choice:** append (the human chose it).
- **Why:** The Log only grows, and the history of acceptances stays visible.

### Decision: Order of who and the arguments
- **Options:**
  - arguments, then `by <who>`;
  - `by <who>` first;
  - parts set off by ` · `.
- **Choice:** arguments, then `by <who>` (the human chose it).
- **Why:** A git name has spaces. With the arguments a closed set per kind, `by` can run to `: ` or the end of the line, and the record reads as a sentence.

## Risks and trade-offs

- **The format changes under this change.** This change is drafted, accepted and partly built in format 1, with `wm` running this checkout.
  - Since the reader follows the stored `record_format`, items 1.1 to 1.3 leave this repository's record read as format 1.
  - Until 1.4, each command writes in its change's format (the human chose this). Item 1.3 adds the format 2 path and tests it on a format 2 record, while the format 1 path and the tests built on it keep working, here too.
  - Item 1.4 changes the fingerprint, adds the migration and raises `RECORD_FORMAT` together. Once `wm` reads and writes only format 2, every format 1 path is dead: 1.4 removes the readers and writers and moves the tests to format 2, keeping format 1 only in the migration's own tests.
  - After 1.4, the planner runs `wm update` on this repository, which migrates this change and the nine archived ones. The human then accepts this change again, and the rest is built in format 2.
- **`--fix` touches human text.** It changes layout only, never wording, and the charter says so. `standard_layout` is idempotent and keeps fenced code and comments, which the tests check. Its result is checked against acceptance and evidence before anything is written.
- **Archived changes are rewritten.** Their files change once, mechanically, in one commit; git keeps them as they were. Old per-item reviews survive only as notes.
- **Who wrote a record is self-reported.** `--by` accepts any name, which is consistent with the charter's non-goal of guarding against someone set on getting around the rails.

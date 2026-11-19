# Reset record format: design

## Context

`RECORD_FORMAT = 3` lives in `record/config.py`. `services/migrations.py` holds the `Migration` class, `pending()`, `migrate()` and `stored_format()`, with `MIGRATIONS = ()`; `integration.update` calls `migrations.migrate` first and prints "Migrated the record" lines. `record/edits.py`'s `set_record_format` is used only by `migrate`. Three places say "Run wm update to migrate" for a record in another format: `require_writable` in `services/common.py`, the `record-format` finding in `services/check.py`, and the `record format` check in `services/doctor.py`. `migrate`'s own refusals give two more reasons, one for an older record and one for a newer.

The readers of older layouts:

- `record/outline.py`'s `OLD_LAYOUT` message, used by `proposal.py` (a fact without a bullet), `charter.py` (a glossary line in another form), `deltas.py` (a delta heading in another case) and `tasks.py` (a trailing `` `build: …` `` tag on an item title);
- `tasks.py`'s `old-record-format` problems: `Blocked:`, `Spec gap:` and `Note:` lines under an item, a `` `review: …` `` tag, and a `## Review` section; and `changes.py`'s `_old_proposal_lines` for `Accepted:`, `Synced:` and `Review override:` lines in a proposal;
- `milestones.py`'s `OLD_FILES` and `record.py`'s `_old_milestone_file`, for active and archived milestones.

0.1.x leftovers: `pointer.py`'s `OLD_POINTER_DIR` and `OLD_POINTER_FILE`, read by `project.py` (`old_pointer`), `record/atlas.py`, `services/setup.py` (`_refuse_in_a_code_repo`), `services/atlas.py` (`point` removes the old pointer) and `services/doctor.py` (the old-place warning); and `doctor.py`'s `OLD_HOOKS_DIR` in the tracked-machine-files check.

`RecordFiles` skips hidden entries, so nothing reads `.waymark/` once the pointer code is gone.

## Approach

1. **One format, one reason.** `RECORD_FORMAT = 1`. A function in `record/config.py`, `other_format_reason(found: int) -> str`, returns the one reason: `The record is in format <found>, and this wm reads only format 1. Install the wm version that wrote it.` `require_writable`, the `record-format` finding and the doctor check all use it, with their severities unchanged.
2. **No migration.** Delete `services/migrations.py`, `set_record_format` and `tests/services/test_migrations.py`. `integration.update` opens the record with `writing=True`, so `require_writable` refuses a record in another format before anything is written, then stages the `.gitkeep` files and the CI workflow and sets up the machine as now. Its shared-change line no longer counts migrations. `wm init` in a clone already opens with `writing=True`, so it gives the same reason. The `update` command's help becomes "Regenerate the files Waymark owns, and add any missing record folders."
3. **This repository's record.** In the same item as step 1, `waymark/config.toml`'s `record_format = 3` becomes `record_format = 1`, by hand, since no command can write it. The CI and `wm check` run against this record, so the number and the code have to change in one commit.
4. **Readers of older shapes go; checks of the current layout stay.** Remove `_old_proposal_lines`, the unbulleted-fact problem in `proposal.py`, the `_OLD_LABELED`, `_OLD_SECTION` and `review` tag handling and `_OLD_FORMAT` in `tasks.py`, and `OLD_FILES` with `_old_milestone_file` and `_check_archived_milestone`. Each such line now falls to the check that applies today: an unbulleted `Owner:` leaves the proposal with no owner, a `Blocked:` line is an `unrecognized-item-line`, a `## Review` section is an unknown section, a `goal.md` is an `unexpected-file`. A trailing `` `build: …` `` tag stays part of the item's title. A glossary line in another form, such as `Record: everything in waymark/`, falls to the existing `glossary-format` problem, which already shows `- **<term>**: <meaning>`; the glossary's own older-format branch is removed. The delta heading-case check is kept, with its wording about the heading expected, without the `OLD_LAYOUT` sentence, and with the problem code `layout`. `OLD_LAYOUT` is removed.
5. **0.1.x leftovers go.** Remove `OLD_POINTER_DIR`, `OLD_POINTER_FILE`, the `old` parameter of `parse_pointer`, `Project.old_pointer`, the `.waymark/atlas.toml` lookups in `project.py`, `record/atlas.py` and `setup.py`, the removal in `atlas.point`, the doctor warning, and `OLD_HOOKS_DIR` from the tracked-machine-files check.
6. **Tests.** Tests for removed behavior are deleted. `tests/record/test_tasks_format2.py` becomes `tests/record/test_tasks_records.py` and `tests/services/test_lifecycle_format2.py` becomes `tests/services/test_lifecycle_records.py`, with the `FORMAT_1` and `FORMAT_2` constants and the tests that use them removed. `tests/support.py`'s `CONFIG` writes `record_format = 1`. New tests are named after the scenarios.
7. **Docs.** `docs/record.md` gives `record_format` as `1` and the one reason; `docs/getting-started.md` drops "when the record needs migrating"; `docs/multi-repo.md` drops the paragraph on `.waymark/atlas.toml`; the CHANGELOG's preamble no longer promises a migration note; `docs/cli.md` is regenerated.

## Decisions

### Decision: Format number
- **Status:** decided
- **Decided by:** human
- **Options:** 1; 2, which no released `wm` wrote; keep 3
- **Choice:** 1
- **Why:** no record outside this repository exists, so the clash with 0.1.x's format 1 doesn't matter, and 1 is the plain first number.

### Decision: How far the cleanup goes
- **Status:** decided
- **Decided by:** human
- **Options:** the migration code only; the migration code and the readers of older layouts; all of that and 0.1.1's atlas pointer and 0.1.0's hooks check
- **Choice:** all of it
- **Why:** nothing made by an older `wm` is left to read.

### Decision: Reason for another format
- **Status:** decided
- **Decided by:** human
- **Options:** one reason for any other format; one for an older record and one for a newer
- **Choice:** one reason
- **Why:** without migrations, an older and a newer record need the same thing, the `wm` version that wrote them.

### Decision: Test files named after format 2
- **Status:** decided
- **Decided by:** human
- **Options:** rename them after what they test; leave them
- **Choice:** rename them
- **Why:** they test the current record lines, and the old names point at a format that no longer exists.

### Decision: Problem code for the kept layout checks
- **Status:** decided
- **Decided by:** human
- **Options:** keep `old-layout`; a new code `layout` for both the glossary and the delta heading checks; `layout` for the delta heading check, with the glossary line left to the existing `glossary-format`
- **Choice:** `layout` for the delta heading check; a glossary line in another form is reported as `glossary-format`
- **Why:** the line isn't from an older format, just in the wrong form; the glossary already has `glossary-format` for that, and a second code for the same mistake would be confusing.

### Decision: How this repository's record changes format
- **Status:** decided
- **Decided by:** planner
- **Options:** edit `record_format` by hand in the same commit as the code; a one-time migration from 3 to 1, removed afterwards
- **Choice:** by hand
- **Why:** a migration written to be deleted is the kind of leftover this change removes, and the edit is one number.

## Open questions

None.

## Risks and trade-offs

- A record made by 0.1.x claims format 1 and is read, not refused; its lines then fail the current checks. Accepted, since no such record exists.
- A user of wm 0.2.0, at format 3, can't move to the next `wm` by `wm update`. Accepted for the same reason; the release notes say so.
- Lines in an older layout get a less specific message than before. They come only from older records, and none exist.
- Between steps 1 and 3 the repository's own `wm` refuses its record, so they land in one commit.

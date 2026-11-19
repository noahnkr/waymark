# Tasks

## 1. Code

- [x] 1.1 Format 1 with one reason, and no migration code
  - **Criteria:**
    - `RECORD_FORMAT` is 1, `wm init` writes `record_format = 1`, and this repository's `waymark/config.toml` holds `record_format = 1` in the same commit
    - a record at format 3 or 2 gets the reason `The record is in format <n>, and this wm reads only format 1. Install the wm version that wrote it.` from `wm update`, `wm init` in a clone, `wm check --fix` and the writing commands, each refused with no file changed, and from `wm check` and `wm doctor` as a finding
    - no message anywhere tells the user to run `wm update` to migrate
    - `services/migrations.py`, `set_record_format` and `tests/services/test_migrations.py` are gone, and `wm update` neither migrates nor prints "Migrated the record"
    - `wm update --help` reads "Regenerate the files Waymark owns, and add any missing record folders."
  - **Verify:**
    - tests named after the scenarios: `test_scenario_new_record_is_format_1`, `test_scenario_record_from_wm_0_2_0` and `test_scenario_reported_by_the_checks` beside the update tests in `tests/adapters/test_integration.py`, `test_scenario_record_in_another_format` for `wm check --fix` and for `wm init` in a clone
    - `grep -rn "migrat" src/` finds nothing
    - `wm check` passes on this repository
  - 2026-11-16 (note) by Noah Roberts: The three older-layout messages that still say to run wm update to migrate (outline.py OLD_LAYOUT, tasks.py _OLD_FORMAT, changes.py _old_proposal_lines) are removed by item 1.2; the grep for migrat in src/ is run again after 1.2.
  - 2026-11-16 (reopened) by Noah Roberts
- [x] 1.2 Remove the readers of older layouts
  - **Criteria:**
    - `OLD_LAYOUT`, `_OLD_FORMAT`, `_OLD_LABELED`, `_OLD_SECTION`, the `review` tag handling, `_old_proposal_lines`, `OLD_FILES`, `_old_milestone_file` and `_check_archived_milestone` are gone, and no problem has the code `old-layout` or `old-record-format`
    - a proposal with `Owner: Ada` and no `- Owner:` line is reported as having no owner, with no message naming `wm update`
    - a delta heading `## Added Requirements` is reported with the code `layout`, showing `## ADDED Requirements`; a glossary line in another form, such as `Record: everything in waymark/`, is reported as `glossary-format`, showing `- **<term>**: <meaning>`
    - a `notes.md` in an active milestone folder is reported as an error that names `milestone.md`
  - **Verify:**
    - `test_scenario_fact_without_a_bullet`, `test_scenario_heading_in_another_case` and `test_scenario_other_file_in_a_milestone`, beside the existing tests for each reader
    - the existing glossary test for the scenario "Old glossary line" passes with the code `glossary-format`
    - `grep -rn "old-layout\|old-record-format\|OLD_LAYOUT" src/ tests/` finds nothing
- [x] 1.3 Remove 0.1.x leftovers
  - **Criteria:**
    - `OLD_POINTER_DIR`, `OLD_POINTER_FILE`, `parse_pointer`'s `old` parameter and `Project.old_pointer` are gone, and a code repo with only `.waymark/atlas.toml` is not found as a code repo
    - `wm atlas point` writes `waymark/config.toml` and doesn't touch `.waymark/`
    - `wm doctor` no longer warns about an old pointer, and its tracked-machine-files check no longer names `.waymark/hooks/`
  - **Verify:**
    - `test_scenario_agent_files_committed` and `test_scenario_nothing_tracked` in `tests/services/test_doctor.py`
    - a test that `.waymark/atlas.toml` alone doesn't make a code repo, in `tests/services/test_atlas.py`
    - `grep -rn "atlas.toml\|waymark/hooks\|OLD_HOOKS" src/` finds nothing
- [x] 1.4 Rename the tests named after format 2
  - **Criteria:**
    - `tests/record/test_tasks_format2.py` is `tests/record/test_tasks_records.py`, and `tests/services/test_lifecycle_format2.py` is `tests/services/test_lifecycle_records.py`, with their docstrings no longer naming a format
    - the `FORMAT_1` and `FORMAT_2` constants, and the tests that use them, are gone
  - **Verify:** `uv run --no-sync pytest` passes, and `grep -rln "format2\|FORMAT_[12]" tests/` finds nothing

## 2. Docs

- [x] 2.1 Docs for one format and no migration
  - **Criteria:**
    - `docs/record.md` gives `record_format` as `1` and says a record in another format is refused with the reason to install the `wm` version that wrote it
    - `docs/getting-started.md` no longer mentions migrating the record
    - `docs/multi-repo.md` no longer describes `.waymark/atlas.toml`
    - the CHANGELOG's preamble no longer says a release tells whether `wm update` migrates, and its released entries are unchanged
    - `docs/cli.md` is regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check` passes, as do `uv run --no-sync pytest tests/test_docs.py` and codespell
    - `grep -rn -i "migrat\|atlas.toml" docs/ README.md` finds only `docs/cli.md`'s generated text, if any

## Log

- 2026-11-16 (accepted) fingerprint efd795a9e3eb34e1 items 1.1, 1.2, 1.3, 1.4, 2.1 by Noah Roberts
- 2026-11-16 (accepted) fingerprint 2f4faf41f1b191ea items 1.1, 1.2, 1.3, 1.4, 2.1 by Noah Roberts
- 2026-11-16 (review) changes 1.1 by wm-reviewer: the settings template, and this repository's config.toml written from it, still say "wm update" advances the record format, breaking 1.1's "no message tells the user to run wm update to migrate" criterion and the "Record format 1" requirement; reword that comment in src/waymark/record/templates/config.toml and waymark/config.toml. Everything else holds and every check passes.
  - [critical] `src/waymark/record/templates/config.toml:7`: the comment `wm init` writes into every record says "wm update" advances the record format, which breaks 1.1's criterion that no message tells the user to run `wm update` to migrate, and the requirement "Record format 1"; the same line is in this repository's `waymark/config.toml:7`
  - [warning] `tools/skills/waymark-release/SKILL.md:33`: the release skill still says to state what `wm update` migrates when the record format changes, which the next release would follow
  - [suggestion] `src/waymark/record/tasks.py:292`: `delegate=False` is now a constant at the only place an item is built; the field could take its value from the `Build:` line alone, or be removed if nothing else sets it
- 2026-11-16 (review) pass by wm-reviewer: the earlier critical finding is fixed in the template and this repository's config.toml, every criterion and scenario holds, all tests and checks pass and wm check is healthy; the release-skill wording is left as a warning
  - [warning] `tools/skills/waymark-release/SKILL.md:33`: the release skill still says "If the record format changed, say what `wm update` migrates", which the next release would follow, though no `wm` migrates any more (carried over from the earlier review, not addressed)
  - [suggestion] `src/waymark/record/tasks.py:292`: `delegate=False` is a constant at the only place an item draft is built; take the value from the `Build:` line alone, or drop the field if nothing else sets it

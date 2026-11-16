# Tasks

## 1. Readers, migration and format 3

- [x] 1.1 Read proposal facts and exploration status as bullets, and check the glossary
  - Criteria: `parse_facts` reads `- Key: value` lines as well as bare ones; `wm new change` writes `- Owner:` and `- Path: short`; an exploration's `- Status:` line gives its state (`open`, `parked`, `led-to <link>`) when present, with `missing-status`, `unknown-status` and `parked-without-reason` reported for a status line that is wrong; a glossary line that is neither `- **<term>**: <meaning>` nor the old `<term>: <meaning>` gives `glossary-format`
  - Verify: tests in `tests/record/` and `tests/services/test_setup.py` for the scenarios "New change", "Parked exploration" and "Parked without a reason"
- [x] 1.2 Read the `Build:` line and criteria as a nested list
  - Criteria: `- Build: delegate` under an item sets `Item.delegate`, and another value gives `unknown-build-tag` naming `delegate`; the trailing tag is still read; bullets under `- Criteria:` are kept as `- <text>` lines in `Item.criteria`, which the fingerprint covers; adding, removing or changing `Build:` withdraws acceptance
  - Verify: tests in `tests/record/test_tasks.py`, `tests/record/test_fingerprint.py` and `tests/services/test_agent_interface.py` for the scenarios "Tagged item", "Unknown build value", "Tag added after acceptance" and "Nested criteria"
- [x] 1.3 Read the new delta sections and rename requirements
  - Criteria: `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements` are read, and the old headings still are; RENAMED holds `- From:`/`- To:` pairs, with a problem for an unpaired line or a name renamed twice; archiving or syncing renames the requirement's heading and keeps its block, before any modification; a missing old name or an existing new name is a conflict; the fingerprint covers the living text of a renamed requirement
  - Verify: tests in `tests/record/test_deltas.py`, `tests/record/test_state.py` and `tests/services/test_archive.py` for the scenarios "Requirement renamed" and "Rename of a missing requirement"
- [x] 1.4 Move to format 3, drop the old layouts and the migrations
  - Criteria: a one-off `services/format_three.py` moves this repository's record to the new layouts, for every change, active and archived, the charter and the explorations, without changing wording; `RECORD_FORMAT` is 3; once it has run here, `format_two.py`, `format_three.py` and their tests are removed, `MIGRATIONS` is empty, and `wm update` refuses an older record with a reason that names its format; the old layouts (bare facts, the old glossary line, the trailing tag, the old delta headings, an exploration without `- Status:`) give `old-layout` naming `wm update`, and their readers go; the tests move to the new layouts; `wm check` is healthy here, and the human accepts this change again
  - Verify: tests in `tests/record/` and `tests/services/test_migrations.py` for the scenarios "Older record", "Old fact line", "Old glossary line" and the old delta headings; then `wm check` and `wm status` here

## 2. Templates, skills and docs

- [x] 2.1 Show the new layouts in the templates and skills
  - Criteria: the proposal, charter, tasks, delta and exploration templates use the new layouts, with capitalized step headings in the charter; `wm-propose`, `wm-update`, `wm-kickoff`, `wm-explore` and `wm-apply` describe them, including RENAMED and the exploration status; the planner runs `wm update` to regenerate the rendered files
  - Verify: `uv run --no-sync pytest tests/adapters tests/record/test_project.py tests/services/test_setup.py`, where a test checks that each template, filled in as `wm new` fills it, reads with no problem; read each changed skill once through as the planner would
- [x] 2.2 Update the docs
  - Criteria: concepts (the files, the formats, the glossary), getting started and the README example show the new layouts; the changelog's unreleased entry has the format 3 change and how to upgrade; the generated docs are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py`, codespell and `wm check`

## Log

- (accepted) 2026-11-16 fingerprint 55bd85a27436cea8 items 1.1 1.2 1.3 1.4 2.1 2.2 by Noah Roberts
- (accepted) 2026-11-16 fingerprint bae055bd98891d65 items 1.1 1.2 1.3 1.4 2.1 2.2 by Noah Roberts

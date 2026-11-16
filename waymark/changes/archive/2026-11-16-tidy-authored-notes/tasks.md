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
  - (reopened) 2026-11-16 by Noah Roberts
- [x] 1.4 Move to format 3, drop the old layouts and the migrations
  - Criteria: a one-off `services/format_three.py` moves this repository's record to the new layouts, for every change, active and archived, the charter and the explorations, without changing wording; `RECORD_FORMAT` is 3; once it has run here, `format_two.py`, `format_three.py` and their tests are removed, `MIGRATIONS` is empty, and `wm update` refuses an older record with a reason that names its format; the old layouts (bare facts, the old glossary line, the trailing tag, the old delta headings, an exploration without `- Status:`) give `old-layout` naming `wm update`, and their readers go; the tests move to the new layouts; `wm check` is healthy here, and the human accepts this change again
  - Verify: tests in `tests/record/` and `tests/services/test_migrations.py` for the scenarios "Older record", "Old fact line", "Old glossary line" and the old delta headings; then `wm check` and `wm status` here
  - (reopened) 2026-11-16 by Noah Roberts

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
- (review) 2026-11-16 changes 1.3 1.4 by wm-reviewer: 1.3 rebuild the renamed heading as `### Requirement: <new>` instead of str.replace, so case or spacing differences and prefix substrings rename correctly, and add tests; 1.4 make an old `<term>: <meaning>` glossary line give `old-layout` naming `wm update` (keep `glossary-format` for other prose), and add tests for "Old fact line", "Old glossary line" and the old delta headings
  - critical `src/waymark/record/deltas.py:_replace_and_remove`: rename rewrites the heading with `str.replace(rename.old, rename.new, 1)`, so when the spec heading differs from the delta's From name in case or spacing (the lookup through `requirement_key` still matches) the merge leaves the heading unchanged and reports nothing; a name that occurs in the `### Requirement: ` prefix is replaced in the wrong place; breaks 1.3 "archiving or syncing renames the requirement's heading" and scenario "Requirement renamed" at the edges
  - critical `src/waymark/record/charter.py:_check_glossary`: an old glossary line `<term>: <meaning>` gives `glossary-format`, not `old-layout` naming `wm update`; breaks 1.4's criterion that the old glossary line gives `old-layout` (the design says `glossary-format`, so the record disagrees with itself)
  - warning `tests/`: no tests for the scenarios "Old fact line", "Old glossary line" (the exact `Record: ...` line) or the old delta headings giving `old-layout`, which 1.4's verification and the charter's tasks rule require; the behavior holds when checked by hand
  - warning `tests/record/test_deltas.py`: no rename test where the From name differs from the spec heading in case or spacing, or appears in the `### Requirement: ` prefix
  - warning `src/waymark/record/explorations.py:parse_exploration`: an old reader is still there (the `Parked:` prefix in the Conclusion is still parsed, with or without a status), though 1.4 says the readers of the old layouts go; a bare `Status: open` without the bullet is accepted and not reported as `old-layout`
  - warning `src/waymark/record/outline.py:OLD_LAYOUT`: the message says to run `wm update` to migrate, but `wm update` migrates nothing in a format 3 record and refuses an older one, so the advice can't fix the problem it reports; the spec asks for this wording, but the human should know it is a dead end
  - suggestion `src/waymark/record/tasks.py:tags`: `del value` and the always-False `delegate` return are leftovers of the removed trailing-tag reader; simplify
  - suggestion `src/waymark/record/templates/delta.md`: the MODIFIED comment says "under the same heading it has in the spec", which is wrong for a requirement that is also renamed in the same delta (it goes under its new name, as `wm-update` says)
- (review) 2026-11-16 pass by wm-reviewer: the earlier changes to 1.3 (heading rebuilt, with tests) and 1.4 (old glossary line gives old-layout, old-layout scenario tests) are made, every criterion and scenario holds, tests, docs check, lint, types and wm check pass; the codespell hit in the change's log must be fixed before CI
  - warning `waymark/changes/tidy-authored-notes/tasks.md:36`: codespell reports the British spelling of "behavior" in the earlier review's log line (added in 9f49a25), so item 2.2's codespell check and CI's spelling job fail; `wm` wrote this record line, so it needs a hand edit or a fix to how `wm` writes review text before pushing
  - warning `src/waymark/record/explorations.py:_status`: an exploration with no `- Status:` line gets `old-layout`, never `missing-status`; 1.1's criteria name `missing-status` and 1.4's name `old-layout` for the same case, so the code follows 1.4 but the record disagrees with itself and `missing-status` is never produced
  - warning `src/waymark/record/explorations.py:parse_exploration`: (carried from the earlier review) the old `Parked:` Conclusion reader is still there, and with status open or led-to a `Parked: ` Conclusion still sets `parked`; 1.4 says the old readers go
  - warning `src/waymark/record/charter.py:_OLD_GLOSSARY_LINE`: only an old glossary line whose term starts with a capital is reported as `old-layout`; `record: everything` gets `glossary-format` instead, which is fragile but meets the scenario
  - suggestion `src/waymark/record/tasks.py:tags`: (carried) `del value` and the always-False `delegate` return are leftovers of the removed trailing-tag reader
  - suggestion `src/waymark/record/templates/delta.md`: (carried) the MODIFIED comment says "the same heading it has in the spec", which is wrong when the requirement is also renamed in the same delta

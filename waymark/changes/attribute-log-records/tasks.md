# Tasks

## 1. Records

- [x] 1.1 Read the new record kinds in a change's Log
  - **Build:** planner
  - **Criteria:**
    - `(ticked) <item>` and `(revised) [<part>, <part>...]: <why>` are record kinds with their shapes, and render and parse back the same
    - `(archived)` is read in a change's Log without a change name, and in a milestone's Log with one, and neither is reported as misplaced
    - `wm check` reports a malformed record of each new kind, naming its shape
  - **Verify:** tests named after the scenarios Record in its shape, Malformed record and Kind before the date, and round-trip tests for the three kinds
- [x] 1.2 Name who wrote each record by its kind
  - **Build:** planner
  - **Criteria:**
    - the human's acts name the git user; the planner's records, the roadmap records included, name `planner for <git user>`, or `planner` without one; agents' endings name `implementer` or `reviewer`
    - `--by` takes the place of the kind's author on every writing command, and `wm accept` still refuses without a git user
    - an implementer's `wm note` without `--by implementer` is refused, naming the flag
    - records already written are read as they are
  - **Verify:** tests named after the scenarios Planner's note, Human's acceptance, Reviewer's verdict, Explicit author, Implementer's note without --by, Blocked item, Resolved item keeps its blocker, Blocker shown with its item, Note in the implementer's pack, Implementer partly done, Reviewer in the background, Item added after a pass, Planned roadmap line, Log of a plan's changes and Member change archived
- [x] 1.3 Record each tick
  - **Build:** planner
  - **Criteria:**
    - `wm tick` writes `(ticked) <item>` into the Log with the checkbox, in one write, naming the git user for a `human` item and `planner for <git user>` for any other, and takes `--by`
    - an implementer's `done` ending writes `(ticked) <item> by implementer`
    - a tick keeps the acceptance
  - **Verify:** tests named after the scenarios Planner's item ticked, Human's item ticked, Implementer's item ticked, Implementer done in the foreground and Implementer in the background
- [x] 1.4 Record the archive in the change's Log
  - **Build:** planner
  - **Criteria:**
    - `wm archive` ends the change's Log with `(archived) by <who>` before it moves the change, in the same write
    - a refused archive writes nothing
  - **Verify:** tests named after the scenarios Archived change and Refused archive
- [x] 1.5 Record revisions, and require one before accepting again
  - **Build:** planner
  - **Criteria:**
    - `wm revise <change> "<why>" [--parts <part>,...] [--by <who>]` writes `(revised)` into the Log, and refuses an unknown part and a change never accepted
    - `wm accept` refuses a change with an `(accepted)` record and no `(revised)` record after the last one, naming `wm revise`
    - implementers and reviewers can't run `wm revise`
  - **Verify:** tests named after the scenarios Revision recorded, Accepting again without a revision, Accepting again after a revision, Unknown part and Accepted again

## 2. Skills and docs

- [x] 2.1 Teach the skills and agents the new records
  - **Build:** planner
  - **Criteria:**
    - `wm-update` runs `wm revise` after each confirmed edit to an accepted change, and when it adds an item, before asking for `wm accept`
    - `wm-apply` and the implementer's definition say how records name who wrote them, and the implementer passes `--by implementer` to its own `wm note`
    - the skills show records with the new authors
  - **Verify:** `tests/test_skills.py`, the adapter snapshots and the full pytest run
- [x] 2.2 Update the docs and CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `docs/record.md` and `docs/concepts.md` describe who records name, and the `(ticked)`, `(archived)` and `(revised)` records
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks

## Log

- 2026-11-20 (accepted) fingerprint d27e4d7c14b6a37d items 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (ticked) 1.3 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.4 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.5 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.2 by planner for Noah Roberts
- 2026-11-20 (review) changes 1.2, 1.3, 2.1, 2.2; covers 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2 by reviewer: README evidence takes today's date from an undated tick in tools/docs.py:392 and will fail tools.docs --check from tomorrow (1.3); wm new change --milestone writes (proposed) without accepting --by (1.2); wm-update records one revision instead of one after each confirmed edit (2.1); docs/record.md milestone Log example and docs/getting-started.md still show the old authors (2.2)
  - [critical] `tools/docs.py:392`: lifecycle.tick(root, CHANGE, item) passes no date, so the README evidence gets (ticked) records dated the day it was generated (2026-11-20, among 2026-01-15 records), and tools.docs --check and the README staleness test will fail from 2026-11-21 (item 1.3; pass DAY and regenerate)
  - [critical] `src/waymark/cli.py:516 and src/waymark/services/setup.py:229`: wm new change --milestone writes a (proposed) record but takes no --by, breaking 1.2's "--by takes the place of the kind's author on every writing command" and the spec's "Every command that writes a record SHALL accept --by <who>"
  - [critical] `docs/record.md:316-320`: the milestone Log example still names "by Ada" for (added), (moved), (proposed) and (dropped), which the new rule writes "by planner for Ada", contradicting the Records section (item 2.2); docs/getting-started.md:132 still shows "(blocked) 1.2 by Sam Doe"
  - [critical] `src/waymark/assets/skills/wm-update/SKILL.md step 5`: wm revise runs once after all edits, while 2.1's criterion and the design say wm-update runs it after each confirmed edit to an accepted change
  - [warning] `src/waymark/hooks/decide.py:309`: _by_implementer passes if "--by implementer" appears anywhere, so "wm note ... --by implementer --by Ada" gets through and argparse writes "by Ada"; no test covers it
  - [warning] `tests/record/evidence/test_records.py`: no test reads records signed with the old names (by wm-implementer, by wm-reviewer), so "records already written are read as they are" holds only by accident
- 2026-11-20 (reopened) 1.2 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.2 by planner for Noah Roberts
- 2026-11-20 (reopened) 1.3 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.3 by planner for Noah Roberts

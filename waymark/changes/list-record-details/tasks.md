# Tasks

## 1. Details

- [x] 1.1 Read and write details under a record
  - **Build:** planner
  - **Criteria:**
    - a sub-line under a `(note)`, `(blocked)`, `(gap)`, `(resolved)` or `(revised)` record is read as a detail; under a review, a bracketed severity is a finding, a bare severity word is still reported as a finding without brackets, and anything else is a detail
    - `wm check` reports a sub-line under any other kind of record as an error naming the kinds that take details, and a detail under a detailed kind that starts with a bracketed severity
    - the Log writer writes details as `  - <detail>` after the record's findings, in the order given
  - **Verify:** tests named after the scenarios Sub-bullet under a record without details and Self-review with a finding and details, the existing "Severity without brackets" test, and parse and write tests for details
- [x] 1.2 Take --detail on the seven writing commands
  - **Build:** planner
  - **Criteria:**
    - `wm note`, `wm block`, `wm gap`, `wm resolve`, `wm review --self`, `wm verdict` and `wm revise` take a repeatable `--detail` and write each one under the record
    - a detail that is empty, runs over a line, or starts with a severity in brackets is refused, and nothing is written
  - **Verify:** tests named after the scenarios Note with details, Self-review with a finding and details and Detail that looks like a finding, and one per command
- [x] 1.3 Read DETAIL lines from an agent's ending
  - **Build:** planner
  - **Criteria:**
    - `DETAIL:` lines before the ending become details, in order, under the `(note)`, `(blocked)` or `(gap)` of an implementer and the `(review)` of a reviewer, after its findings
    - a `done` ending writes its `(ticked)` record without details
  - **Verify:** tests named after the scenarios Reviewer's details and Implementer's details, and one for a `done` ending with a `DETAIL:` line
- [x] 1.4 Take --built and --differs more than once
  - **Build:** planner
  - **Criteria:**
    - a value given once is written inline on its label's line, as before
    - several values are written as nested bullets under a bare label, in the order given, and `wm pr` shows them
  - **Verify:** tests named after the scenarios Archived with an outcome, Nothing differs and Outcome as a list
- [x] 1.5 Show details in the views, packs and pull request
  - **Build:** planner
  - **Criteria:**
    - `wm show --json` gives each record `details`, at `show.change` version 5, and the schema says so; the text view draws them under their record, after findings
    - the implement pack's notes and the review pack's earlier reviews carry their details, at pack version 4, and their text shows them
    - `wm pr` writes each record's details under it
  - **Verify:** a test named after the scenario Details in the views, the schema tests, and tests for the packs and `wm pr`

## 2. Skills and docs

- [x] 2.1 Teach the skills and agents to give details
  - **Build:** planner
  - **Criteria:**
    - `wm-apply` and `wm-update` say to give several points as `--detail` lines rather than one long text
    - `wm-archive` says `--built` and `--differs` may be given more than once
    - the implementer and reviewer definitions describe `DETAIL:` lines before the ending
  - **Verify:** `tests/test_skills.py`, the adapter snapshots and the full pytest run
- [x] 2.2 Update the docs and CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `docs/record.md` and `docs/concepts.md` describe details under records, `DETAIL:` lines and an Outcome as a list
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks
- [x] 2.3 Keep a detail that starts with a severity word from reading as a finding
  - **Build:** planner
  - **Criteria:**
    - under a review, a sub-line is reported as a finding without its brackets only when it has a finding's shape: a severity word followed by `:` or by a place in backticks
    - a detail written by `wm`, such as `warning signs remain`, is read back as a detail under a review, and `wm check` reports nothing about it
    - `--detail` and `DETAIL:` lines refuse a detail with a finding's shape, bracketed or not, such as `warning: the retry is slow`, and nothing is written
  - **Verify:** the existing "Severity without brackets" test, and tests named after the scenarios Detail with a finding's shape but no brackets and Detail that starts with a severity word

## Log

- 2026-11-20 (accepted) fingerprint 921764255ebc4141 items 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (ticked) 1.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.2 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.3 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.4 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.5 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.2 by planner for Noah Roberts
- 2026-11-20 (review) changes 2.2; covers 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2 by reviewer: docs/record.md's details example leaves its code fence open, so everything after it renders as code; close the fence on its own line, and add DETAIL lines to the ending blocks in docs/skills.md and the concepts.md table while there. Items 1.1-1.5 and 2.1 meet their criteria and every check passes.
  - [critical] `docs/record.md:462`: the closing code fence of the details example is followed by text ("``` A later record"), so the fence never closes and the rest of the Records section, its table included, renders as one code block; put the fence on its own line (item 2.2, rule 7)
  - [warning] `src/waymark/record/evidence/records.py:466`: check_detail accepts a detail that starts with a bare severity word ("warning signs remain"), which the Log parser (tasks.py review_sub_line) then reports as malformed-finding under a review, so `wm review --self --detail`, `wm verdict --detail` or a reviewer's DETAIL line can write a record that `wm check` reports as an error
  - [warning] `docs/skills.md:305`: the reviewer's and implementer's ending blocks, and the "Ends with" row in docs/concepts.md:312, don't mention DETAIL lines; they are now incomplete and no item covers them (rule 4)
  - [suggestion] `tests/services/test_lifecycle_records.py`: --detail is tested only at the service level, and `wm resolve <change> review` with details is untested; parsing a few CLI invocations would cover the wiring in cli.py
  - [suggestion] `src/waymark/record/artifacts/tasks.py:367`: a bracketed severity under a detailed non-review record is reported as misplaced-finding, not the malformed-detail the design names; it still meets the criterion, but code and design disagree
- 2026-11-20 (reopened) 2.2 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.2 by planner for Noah Roberts
- 2026-11-20 (revised) 2.3 by planner for Noah Roberts: the review found a detail starting with a severity word reads as a finding
  - wm wrote such a detail, then wm check reported it under a review
  - added 2.3 to read it as a detail unless it has a finding's shape
- 2026-11-20 (ticked) 2.3 by planner for Noah Roberts
- 2026-11-20 (review) changes 2.3; covers 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3 by reviewer: check_detail still accepts details like "warning: <text>" that the Log parser reports as malformed-finding under a review, so 2.3's criterion that wm-written details read back clean doesn't hold; refuse them in check_detail and revise the review delta and design to the narrowed rule; the earlier review's fence and DETAIL-docs fixes are made, and all checks pass
  - [critical] `src/waymark/record/evidence/records.py:660`: check_detail accepts a detail with a finding's shape but no brackets ("warning: the retry is slow", "critical `path` covered"), which review_sub_line (tasks.py:527) reports as malformed-finding, so wm still writes a review detail that wm check reports as an error (item 2.3, second criterion); refuse what starts_with_severity matches too, and test it
  - [warning] `waymark/changes/list-record-details/specs/review.md:6`: the review delta still says any sub-line starting with a severity without brackets SHALL be reported as a finding, and design.md step 1 and its Risks say the same, while item 2.3 narrowed this to a severity word followed by ":" or a place in backticks; the delta and design disagree with the code and would archive the old rule
  - [suggestion] `src/waymark/record/artifacts/tasks.py:514`: a bracketed severity under a detailed non-review record is still reported as misplaced-finding rather than the malformed-detail the design names
- 2026-11-20 (resolved) by Noah Roberts: refuse a detail with a finding's shape in --detail and DETAIL lines, reword the review and records deltas and the design to the narrowed rule, rebuild 2.3 and review again
- 2026-11-20 (revised) specs/records, specs/review, design, 2.3 by planner for Noah Roberts: one rule for a finding's shape, as the human decided on the second review
  - a detail with a finding's shape, bracketed or not, is refused
  - the review delta and the design name the narrowed rule
  - a bracketed severity under a note is misplaced-finding, as the code does
- 2026-11-20 (accepted) fingerprint 1d3889e35976a2ca items 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3 by Noah Roberts

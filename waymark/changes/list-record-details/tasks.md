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

## Log

- 2026-11-20 (accepted) fingerprint 921764255ebc4141 items 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (ticked) 1.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.2 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.3 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.4 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.5 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.2 by planner for Noah Roberts

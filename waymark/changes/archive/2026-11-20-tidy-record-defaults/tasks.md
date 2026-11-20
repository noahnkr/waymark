# Tasks

## 1. Record defaults

- [x] 1.1 Write the Review line with every new change, and require it
  - **Build:** planner
  - **Criteria:**
    - `wm new change` writes `- **Review:** <default_review>` under the Owner line, or `self` on the short path when the default is `independent`
    - the review level is read only from the proposal's Review line, and `wm check` reports an active change without one as an error that shows `- **Review:** <level>`
    - the `review-level` warning and the propose step's guidance tell the planner to set the Review line's value, not to add the line
  - **Verify:** tests named after the scenarios Level from the proposal, Default written at creation, Default on the short path, Review line missing and New change; the full pytest run and `wm check`
- [x] 1.2 Make charter glossary entries bold with `wm check --fix`
  - **Build:** planner
  - **Criteria:**
    - `wm check --fix` rewrites `- <term>: <meaning>` and `- **<term>**: <meaning>` in the charter's glossary into `- **<term>:** <meaning>`, and names the charter as fixed
    - lines outside the glossary, comments and fenced code in the charter are unchanged
  - **Verify:** a test for the scenario Glossary entry made bold, and the existing fix tests
- [x] 1.3 Drop the comment under the exploration template's Status line
  - **Build:** planner
  - **Criteria:** `wm new exploration <name>` writes the Status line followed directly by `## Context`, and the other sections keep their comments and examples
  - **Verify:** a test that a new exploration has no comment between its Status line and `## Context`, and the Template examples tests

## 2. Docs and skills

- [x] 2.1 Update the skill, docs and CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `wm-propose` step 6 says the Review line is already written with the project default, and the planner sets its value
    - `docs/record.md` shows the Review line as one of every proposal's facts, and says `--fix` makes glossary entries bold
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks

## Log

- 2026-11-20 (accepted) fingerprint 6bb71a691ee08d67 items 1.1, 1.2, 1.3, 2.1 by Noah Roberts
- 2026-11-20 (self-review) covers 1.1, 1.2, 1.3, 2.1 by Noah Roberts: Every criterion of 1.1 to 2.1 holds and each delta scenario has a passing test: wm new change writes the default Review line (self on the short path), a missing line is missing-review, wm check --fix bolds charter glossary entries only inside the Glossary, and new explorations have no Status comment. The full checks (pytest 1463, ruff, mypy, codespell, tools.docs --check) and wm check pass; the one wm check warning is this change's own self level on the short path.
  - [suggestion] `src/waymark/record/artifacts/changes.py`: review_level still falls back to default_review when the line is missing; an active change is reported for it, so the level only stands in until the line is written
  - [suggestion] `src/waymark/services/setup.py`: the Review line is written after Milestone, After and Path rather than straight under Owner; it is under the Owner line, as the requirement says, but not next to it

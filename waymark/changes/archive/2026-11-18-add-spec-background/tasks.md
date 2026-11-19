# Tasks

## 1. Code

- [x] 1.1 Background in specs and deltas
  - **Criteria:**
    - a spec and a delta may have a `## Background` section, read as text; a spec's Background after its Purpose and before its Requirements is healthy
    - an empty Background in a spec or a delta is reported as an error on its heading that says the Background is empty
    - archiving or syncing a delta with a Background replaces the spec's Background whole, or inserts the section right before `## Requirements` when the spec has none, or writes it after the Purpose in a new spec; the requirements are unchanged
    - re-running a sync that has already set the Background writes nothing
  - **Verify:**
    - `test_scenario_background_set_by_a_delta`, `test_scenario_background_replaced` and `test_scenario_empty_background`, beside the existing delta and archive tests
    - `wm check` passes on this repository
- [x] 1.2 Background in the packs
  - **Criteria:**
    - the implement and review packs hold `backgrounds`, one `{"spec", "text"}` entry for each spec the change has a delta for with a Background in the delta or the spec, the delta's first; specs with neither are left out
    - the text output shows each Background under its spec's name, and no schema version changes
  - **Verify:**
    - `test_scenario_background_of_a_touched_spec` and `test_scenario_background_from_the_delta`, beside the existing context-pack tests

## 2. Guidance, skills and docs

- [x] 2.1 Where a fact goes
  - **Criteria:**
    - the delta template has a `## Background` section whose comment says what goes there, with a good and a bad example, and to remove it unless the change sets the Background
    - the specs step's guidance holds the rule: what the system does is a requirement, a fact about the area its Background, a fact about an outside system a resource, a fact for the whole project the charter's Context
    - `wm-propose` says the same where it drafts the deltas
  - **Verify:**
    - a test that the specs step's guidance holds the rule, beside the existing step-guidance tests, and the existing template-example tests pass
    - `uv run --no-sync pytest tests/test_skills.py tests/adapters` passes
- [x] 2.2 Docs for spec background
  - **Criteria:**
    - `docs/record.md` gives Background among a spec's and a delta's sections, and says a delta's Background replaces the spec's at archive
    - `docs/concepts.md` gives the four places a fact goes
    - `docs/json.md` is regenerated, and the CHANGELOG's Unreleased section notes the section and the packs' `backgrounds`
  - **Verify:** `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- 2026-11-18 (accepted) fingerprint b111aa8b43d96dd8 items 1.1, 1.2, 2.1, 2.2 by Noah Roberts
- 2026-11-18 (accepted) fingerprint 0398f7683dce131c items 1.1, 1.2, 2.1, 2.2 by Noah Roberts
- 2026-11-18 (review) pass covers 1.1, 1.2, 2.1, 2.2 by wm-reviewer: every criterion of 1.1, 1.2, 2.1 and 2.2 holds, all five scenarios have passing tests, and the tests, wm check, the docs check, codespell, ruff and mypy all pass
  - [suggestion] `src/waymark/views/render.py: _spec_lines`: the Background text is not fenced as the requirements and deltas are, so a Background holding `##` headings would blend into the pack's own headings
  - [suggestion] `tests/record/test_deltas.py`: the archive scenarios are tested through merge_delta and delta_is_merged, not through a full archive or sync run

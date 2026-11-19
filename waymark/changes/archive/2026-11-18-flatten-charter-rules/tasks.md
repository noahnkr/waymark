# Tasks

## 1. Code

- [x] 1.1 Rules as one numbered list
  - **Criteria:**
    - the charter's Rules are read as one string and checked like Goals and Constraints: a bullet, a `###` heading or any other line is reported with the form `1. <text>`, and empty Rules are healthy
    - the step-heading parsing and its problems (`unknown-step` and the repeated step) are gone
    - the charter template writes `## Rules` with a comment and a good and bad example, and no step headings
    - this repository's `waymark/charter.md` holds its eight rules as one numbered list, in the same commit, and `wm check` passes on it
  - **Verify:**
    - `test_scenario_step_heading_under_rules` and `test_scenario_no_rules` beside the existing test for the scenario Bulleted goal, and the existing Old glossary line test still passes
    - `wm check` passes on this repository
- [x] 1.2 Every agent gets every rule
  - **Criteria:**
    - `wm instructions` gives the whole Rules as `rules` at every step, explore included, titled "Project rules" in the text output and left out when empty
    - the explore, implement and review packs give the whole Rules as `rules`, titled "Project rules" in their text output
    - no schema version changes
  - **Verify:**
    - `test_scenario_same_rules_at_two_steps` and `test_scenario_no_rules` (instructions) beside the existing step-guidance tests, and `test_scenario_reviewer_gets_every_rule` beside the context-pack tests

## 2. Skills and docs

- [x] 2.1 Skills and docs for one list of rules
  - **Criteria:**
    - `wm-kickoff` asks for the project's rules as one list; `wm-explore` and `wm-apply` no longer speak of rules for a step
    - `docs/record.md` describes `## Rules` as a numbered list every agent gets at every step, and `docs/concepts.md` no longer says an implementer sees only the apply rules
    - the CHANGELOG's Unreleased section notes the change, and `docs/cli.md` and `docs/json.md` are regenerated if they changed
  - **Verify:**
    - `uv run --no-sync pytest tests/test_skills.py tests/adapters tests/test_docs.py`, `uv run --no-sync python -m tools.docs --check` and codespell pass
    - `grep -rn -i "rules for this step\|step's rules" src/ docs/` finds nothing

## Log

- 2026-11-18 (accepted) fingerprint c7fbdef466aa348e items 1.1, 1.2, 2.1 by Noah Roberts
- 2026-11-18 (review) pass covers 1.1, 1.2, 2.1 by wm-reviewer: every criterion of 1.1, 1.2 and 2.1 holds and every scenario in the three deltas is met; pytest, tools.docs --check, codespell, ruff, mypy and wm check all pass
  - [suggestion] `src/waymark/services/context.py:3-8`: module docstring still says implementer/reviewer packs carry "apply rules"/"review rules"; they now carry the project's whole Rules
- 2026-11-18 (note) 1.1 by Noah Roberts: Charter.rules became a string, so instructions.py and context.py now pass it whole in place of one step's text, to keep the build green; item 1.2 adds the Project rules titles and its scenario tests

# Tasks

## 1. Guidance and skills

- [x] 1.1 Give the specs and tasks steps the writing and sizing rules
  - **Criteria:**
    - `wm instructions` for the specs step gives, in its guidance, the four rules for writing requirements, worded as in the requirement "Writing and sizing rules"
    - `wm instructions` for the tasks step gives, in its guidance, the four rules for sizing items
    - the other steps' guidance is unchanged
  - **Verify:**
    - tests in `tests/services/test_agent_interface.py` for the scenarios "Specs step" and "Tasks step"
    - `uv run --no-sync python -m tools.docs --check`
- [x] 1.2 Rewrite the drafting skills to the layout
  - **Criteria:**
    - `wm-propose`, `wm-update`, `wm-kickoff` and `wm-explore` each have Role, Inputs, Steps, their own sections, Quality bar, Show the human, When to stop and Rules, in that order, with Rules starting with the shared-rules line
    - `wm-propose` has a Questions step before drafting and a Consistency check step before acceptance, and its Show the human gives the fixed acceptance summary
    - `wm-kickoff`'s steps are the interview script, one charter section at a time, each answer written in before the next question
    - `wm-explore`'s steps read what the record says, state the questions, weigh two or more approaches with what speaks for and against each, and recommend one
    - `wm-propose` and `wm-update` point at the writing and sizing rules in `wm instructions` instead of restating them
    - every step and rule of the four skills' old text is kept, moved into the layout, or covered by the shared rules
  - **Verify:**
    - the assets tests in `tests/`
    - read each of the four skills against its old text
- [x] 1.3 Rewrite the working skills to the layout, and hold it with a test
  - **Criteria:**
    - `wm-apply`, `wm-archive`, `wm-pr`, `wm-fix` and `wm-onboard` follow the same layout, each with its fixed Show the human and its When to stop
    - every step and rule of the five skills' old text is kept, moved into the layout, or covered by the shared rules
    - `tests/test_skills.py` checks every skill in `assets.SKILLS`: Role, Inputs and Steps first, Quality bar, Show the human, When to stop and Rules last, nothing else in those places, and the shared-rules line first under Rules; a failure names the skill and the heading out of place
  - **Verify:**
    - `tests/test_skills.py` for the scenarios "Installed skills" and "A section out of place"
    - read each of the five skills against its old text

## 2. Docs

- [x] 2.1 Update the docs and the changelog
  - **Criteria:**
    - concepts names the skill layout and says the writing and sizing rules come from `wm instructions`
    - the changelog lists the rewritten skills, the new `wm-propose` steps, and the writing and sizing rules
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

## Log

- 2026-11-16 (accepted) fingerprint 8c8e48bc323ed4e0 items 1.1, 1.2, 1.3, 2.1 by Noah Roberts
- 2026-11-16 (self-review) by Noah Roberts: Checked against the four scenarios, the design and each item's criteria. Installed skills and A section out of place are held by tests/test_skills.py over all nine shipped skills; Specs step and Tasks step by tests in test_agent_interface.py. Each of the nine skills was read against its old text: every step and rule is kept, moved into the layout, or covered by the shared rules or the writing rules in wm instructions. wm-propose has the Questions and Consistency check steps and the fixed acceptance summary; wm-kickoff the ordered interview; wm-explore the record-questions-approaches-recommendation method. Full checks pass: pytest (1122), ruff, mypy, codespell, tools.docs --check, wm check.
  - [suggestion] `tests/test_skills.py:test_scenario_a_section_out_of_place`: the scenario is about the test that holds the layout, not something a user sees
  - [suggestion] `.claude/skills`: this machine's installed copies keep the old text until wm init refreshes them

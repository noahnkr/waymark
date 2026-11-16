# Tasks

## 1. Guidance and skills

- [x] 1.1 Give the specs and tasks steps the writing and sizing rules
  - Criteria:
    - `wm instructions` for the specs step gives, in its guidance, the four rules for writing requirements, worded as in the requirement "Writing and sizing rules"
    - `wm instructions` for the tasks step gives, in its guidance, the four rules for sizing items
    - the other steps' guidance is unchanged
  - Verify:
    - tests in `tests/services/test_agent_interface.py` for the scenarios "Specs step" and "Tasks step"
    - `uv run --no-sync python -m tools.docs --check`
- [x] 1.2 Rewrite the drafting skills to the layout
  - Criteria:
    - `wm-propose`, `wm-update`, `wm-kickoff` and `wm-explore` each have Role, Inputs, Steps, their own sections, Quality bar, Show the human, When to stop and Rules, in that order, with Rules starting with the shared-rules line
    - `wm-propose` has a Questions step before drafting and a Consistency check step before acceptance, and its Show the human gives the fixed acceptance summary
    - `wm-kickoff`'s steps are the interview script, one charter section at a time, each answer written in before the next question
    - `wm-explore`'s steps read what the record says, state the questions, weigh two or more approaches with what speaks for and against each, and recommend one
    - `wm-propose` and `wm-update` point at the writing and sizing rules in `wm instructions` instead of restating them
    - every step and rule of the four skills' old text is kept, moved into the layout, or covered by the shared rules
  - Verify:
    - the assets tests in `tests/`
    - read each of the four skills against its old text
- [ ] 1.3 Rewrite the working skills to the layout, and hold it with a test
  - Criteria:
    - `wm-apply`, `wm-archive`, `wm-pr`, `wm-fix` and `wm-onboard` follow the same layout, each with its fixed Show the human and its When to stop
    - every step and rule of the five skills' old text is kept, moved into the layout, or covered by the shared rules
    - `tests/test_skills.py` checks every skill in `assets.SKILLS`: Role, Inputs and Steps first, Quality bar, Show the human, When to stop and Rules last, nothing else in those places, and the shared-rules line first under Rules; a failure names the skill and the heading out of place
  - Verify:
    - `tests/test_skills.py` for the scenarios "Installed skills" and "A section out of place"
    - read each of the five skills against its old text

## 2. Docs

- [ ] 2.1 Update the docs and the changelog
  - Criteria:
    - concepts names the skill layout and says the writing and sizing rules come from `wm instructions`
    - the changelog lists the rewritten skills, the new `wm-propose` steps, and the writing and sizing rules
    - the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

## Log

- (accepted) 2026-11-16 fingerprint 8c8e48bc323ed4e0 items 1.1 1.2 1.3 2.1 by Noah Roberts

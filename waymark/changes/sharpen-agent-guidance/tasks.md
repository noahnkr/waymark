# Tasks

## 1. Guidance in the packs

- [x] 1.1 Give the review pack and step the severity rubric, and the implement pack the stopping rules
  - Criteria:
    - a new `services/guidance.py` holds `SEVERITY_RUBRIC` and `STOPPING_RULES`, worded as in the requirements "Severity rubric" and "Stopping rules"
    - the review pack holds `severity_rubric`, and the implement pack `stopping_rules`; their markdown shows "## Severity rubric" and "## When to stop" just before the ending
    - every `wm instructions` payload holds `severity_rubric`: the rubric at the review step, empty elsewhere; the text shows "Severity rubric" after "Checklist" when it isn't empty
    - the schemas gain the fields, the versions stay, and `docs/json.md` is regenerated
  - Verify:
    - tests in `tests/services/test_agent_interface.py` for the scenarios "Review pack", "Self-review" and "Implement pack"
    - `uv run --no-sync python -m tools.docs --check`

## 2. Agents, skill and docs

- [ ] 2.1 Point the agents and `wm-apply` at the rubric and the stopping rules
  - Criteria:
    - `wm-reviewer` grades each finding by the pack's severity rubric, in place of its own one-line severity definitions; its format lines and verdict rules stay
    - `wm-implementer` has a "When to stop" section that follows the pack's stopping rules; "Don't guess" stays
    - `wm-apply`'s self-review grades each finding by the rubric `wm instructions` gives at the review step, and the skill still follows the layout `tests/test_skills.py` holds
  - Verify:
    - the assets tests and `tests/test_skills.py`
    - read the two agents and `wm-apply` against their old text
- [ ] 2.2 Update the docs and the changelog
  - Criteria:
    - concepts says the review pack and step give the severity rubric, and the implement pack the stopping rules
    - the changelog lists the rubric, the stopping rules and the `severity_rubric` and `stopping_rules` fields
    - the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

## Log

- (accepted) 2026-11-16 fingerprint c9c1cabd18360233 items 1.1 2.1 2.2 by Noah Roberts

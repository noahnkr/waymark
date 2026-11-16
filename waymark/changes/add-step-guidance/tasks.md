# Tasks

## 1. Guidance and checks

- [x] 1.1 Give each drafting step a checklist, and every step the shared rules
  - Criteria:
    - `wm instructions` for propose, specs, design and tasks gives the checklist the design lists for that step, each check with `text` and `enforced`; every other step, and explore, gives an empty `checklist`
    - each enforced check names the problem codes that enforce it, and a test holds that every code named is one `wm check` can report
    - every payload, explore included, holds the same `shared_rules`: the five rules of the requirement "Shared rules"
    - the text output shows "Shared rules", then "What to do", then "Checklist", marking enforced checks with "wm"
    - the JSON schema gains `checklist` and `shared_rules`, the version stays 1, and `docs/json.md` is regenerated
  - Verify:
    - tests in `tests/services/test_agent_interface.py` for the scenarios "Specs checklist", "Apply has no checklist" and "Shared rules at every step"
    - a test in `tests/views/` that the text output shows the three blocks in order
    - `uv run --no-sync python -m tools.docs --check`
- [x] 1.2 Check that items say how they are done and decisions weigh options
  - Criteria:
    - for an active change, an item without a `- Criteria:` or `- Verify:` line gives `item-incomplete` on the item, naming the missing line
    - `Decision.options` holds the bullets under `- Options:`, or else the line split on ";" and the word "or"; for an active change, a decision with fewer than two gives `decision-options` on its heading
    - archived changes aren't checked for either
    - `wm check` is healthy here
  - Verify:
    - tests in `tests/record/test_authored_formats.py` for the scenarios "Item without verification", "One option" and "Options as a list"
    - `wm check` here

## 2. Skills and docs

- [x] 2.1 Point the skills at the shared rules
  - Criteria:
    - each of the nine skills' `## Rules` drops the rules the shared list covers, keeps the rules particular to it, and says the shared rules from `wm instructions` apply, with `wm instructions explore` when no change is in hand
    - `wm-propose` and `wm-update` say to work through the step's checklist before moving on
  - Verify:
    - the assets tests in `tests/`
    - read each skill: no rule it used to state is lost, either kept or covered by the shared list
- [ ] 2.2 Update the docs and the changelog
  - Criteria:
    - concepts says `wm instructions` gives each drafting step a checklist and every step the shared rules
    - the changelog lists the checklist, the shared rules, `checklist` and `shared_rules` in the JSON, and the two new checks
    - the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

## Log

- (accepted) 2026-11-16 fingerprint 1c162917de45e705 items 1.1 1.2 2.1 2.2 by Noah Roberts

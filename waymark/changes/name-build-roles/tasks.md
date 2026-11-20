# Tasks

## 1. Roles

- [x] 1.1 Read the Build line as one of three roles
  - **Build:** planner
  - **Criteria:**
    - `BuildRole` in `record/terms.py` holds `planner`, `implementer` and `human`, and `Item.build` is a `BuildRole` or None, with no `delegate` field left
    - `wm check` reports any other Build value, `delegate` included, and a missing Build line, naming `planner`, `implementer` and `human`
    - `wm instructions` sends an `implementer` item to an implementer as it sent a `delegate` one, and the tasks step's guidance names the three roles
    - the tasks template's example and comment use the three roles
  - **Verify:** tests named after the scenarios Implementer item, Unknown build value, Item without a Build line, Build line last, Item lines put in order and Build changed after acceptance; the full pytest run and `wm check`
- [x] 1.2 Hand a human item to the human, and keep implementers off it
  - **Build:** planner
  - **Criteria:**
    - for a `human` item, `wm instructions` tells the planner to give the human the item's Criteria and Verify as the steps, to tick it with `wm tick` only after their yes, and to `wm block` it with what it waits on when they can't do it now; its commands are `wm tick` and `wm block`, and it doesn't mention building the item or starting an implementer
    - starting an implementer on a `human` item is refused, with a reason that says the human does it and the planner ticks it after their yes
  - **Verify:** tests named after the scenarios Item for the human, Human item waits and Implementer on a human item
- [x] 1.3 Tell a review which items the human did
  - **Build:** planner
  - **Criteria:**
    - each item in the implement and review packs carries its `build` role, and the packs' schema version is 3
    - the review pack and the review step's guidance name the `human` items and say their ticks are the human's confirmation, while what they left in the repo is still checked; with no `human` item, neither says anything about them
  - **Verify:** tests named after the scenarios Human item in the review pack and Self-review with a human item, and one for a change with no human item
- [x] 1.4 Show each item's role in `wm show`
  - **Build:** planner
  - **Criteria:**
    - `wm show <change> --json` gives each item `build` (the role, or null) and no `delegate`, at `show.change` version 4, and the schema says so
    - the text view tags an item `build: implementer` or `build: human`, and tags a `planner` item with nothing
  - **Verify:** a test named after the scenario Role in the JSON, the schema tests, and a text view test for the tags

## 2. Skills, docs and the archive

- [x] 2.1 Name the three roles in the skills and agent definitions
  - **Build:** planner
  - **Criteria:**
    - `wm-propose` step 7 offers `planner`, `implementer` and `human`, saying when each fits, and `human` for work only the human can do, such as filling in a form, a manual test or setting up a platform
    - `wm-apply` builds `planner` items, delegates `implementer` items and hands `human` items to the human, ticking them after the human's yes
    - the agent definitions and the other skills say `implementer` where they named the `delegate` value, and keep "delegate" only as a verb
  - **Verify:** `tests/test_skills.py` and the full pytest run
- [x] 2.2 Update the docs and CHANGELOG, and the archived task lists
  - **Build:** planner
  - **Criteria:**
    - `docs/` and the README name the three roles, and the JSON reference shows `build`
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines, and says to change `delegate` to `implementer` in any active change
    - the 2 archived task lists that held a `- **Build:** delegate` item line read `- **Build:** implementer` there, changed by hand, and nothing else in them changes
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - no item line reads `- **Build:** delegate` in an archived task list
    - the full checks

## Log

- 2026-11-20 (accepted) fingerprint 758851e46b4f1ce8 items 1.1, 1.2, 1.3, 1.4, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (accepted) fingerprint ad57878a4af8a726 items 1.1, 1.2, 1.3, 1.4, 2.1, 2.2 by Noah Roberts

# Tasks

## 1. Reopening

- [x] 1.1 Reopen any ticked item with a reason
  - **Build:** planner
  - **Criteria:**
    - `(reopened)` reads and renders with or without a reason after a colon
    - `wm reopen <change> <item> --reason "<why>"` reopens a ticked item of an accepted change that no open review names, takes its tick off and writes `(reopened) <item>` with the reason, keeping the acceptance
    - without `--reason` such an item is refused naming `--reason`; an unticked item and an unaccepted change are refused; an item a review names reopens as before, `--reason` optional
  - **Verify:** tests named after the scenarios Ticked item reopened with a reason, No reason given, Item not ticked and Reopened with a reason, and the existing reopen tests
- [x] 1.2 Review a reopened item again
  - **Build:** planner
  - **Criteria:**
    - a passing review covers an item only when no `(reopened)` record for it follows the review
    - an item reopened after a pass and ticked again makes the next step a review of that item only, and `wm archive` refuses the change until one passes
  - **Verify:** tests named after the scenarios Item reopened after a pass, Item added after a pass and Archive before the added item is reviewed
- [x] 1.3 Warn about a revised item left ticked
  - **Build:** planner
  - **Criteria:**
    - `wm check` warns, naming the item and `wm reopen`, when a `(revised)` record names an item that its Log shows ticked then, and no later `(ticked)` or `(reopened)` record for it follows
    - it says nothing once the item is reopened or ticked again, nor when the item wasn't ticked at the revision
  - **Verify:** tests named after the scenarios Revised item still ticked, Revised item reopened and Revised item not yet ticked

- [x] 1.4 Ask for the reopen in wm instructions, and refuse the archive
  - **Build:** planner
  - **Criteria:**
    - a ticked item that a `(revised)` record names, with no later `(ticked)`, `(reopened)` or item `(resolved)` record, makes the next step an apply of that item, right after an escalated review and before any other step
    - that step's first command is `wm reopen <change> <item> --reason "<what the revision changed>"`, without `--reason` when a review names the item
    - `wm archive` refuses such a change, naming the item and `wm reopen`, even with `--override`, and writes nothing
    - the `wm check` warning and this step read the Log the same way
  - **Verify:** tests named after the scenarios Revised item is the next step, Archive refused for a revised item, Revised item still ticked, Revised item reopened and Revised item not yet ticked

## 2. Skills and docs

- [x] 2.1 Teach the skills to reopen
  - **Build:** planner
  - **Criteria:**
    - `wm-update` says a revised ticked item goes back to apply once the human accepts again, in its steps, Show the human and When to stop, and that `wm instructions` will ask for the reopen
    - `wm-apply` follows the reopen command `wm instructions` gives, and its `resolve-items` step reopens the items the human's decision on an escalated review names, after recording the decision
  - **Verify:** `tests/test_skills.py` and the full pytest run
- [x] 2.2 Update the docs and CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `docs/record.md` and `docs/concepts.md` describe `wm reopen --reason`, a reopened item's review, the `revised-ticked-item` warning, and that `wm instructions` asks for the reopen and `wm archive` refuses until it is done
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks

## Log

- 2026-11-20 (accepted) fingerprint 129122ca3ad7b588 items 1.1, 1.2, 1.3, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (ticked) 1.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.2 by planner for Noah Roberts
- 2026-11-20 (ticked) 1.3 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.2 by planner for Noah Roberts
- 2026-11-20 (review) changes 2.1; covers 1.1, 1.2, 1.3, 2.1, 2.2 by reviewer: wm-update tells the planner to run wm reopen right after revising a ticked item, which is refused because the revision withdrew acceptance, and the skill stops before re-acceptance; it should say to reopen after wm accept when acceptance was withdrawn. 1.1, 1.2, 1.3 and 2.2 meet their criteria and scenarios.
  - [critical] `src/waymark/assets/skills/wm-update/SKILL.md step 3`: it says to reopen a revised ticked item right after wm revise, but changing a ticked item's definition withdraws acceptance and wm reopen refuses a withdrawn change, while step 5 and When to stop end the skill until the human accepts again, so 2.1's criterion (wm-update reopens each ticked item a revision changes, with --reason) does not hold; fix by telling the planner to reopen right after the revision only when acceptance holds (for example an added item), and otherwise to reopen each revised ticked item once the human has run wm accept, in step 5, Show the human and When to stop as well
  - [warning] `src/waymark/services/check.py _revised_ticked_findings`: an item (resolved) record also clears a pending warning, but the requirement names only later (ticked) or (reopened) records; no test covers this
  - [warning] `tests/test_skills.py`: no test checks the new reopen text in wm-update or wm-apply, so a later edit could remove it unnoticed
  - [suggestion] `src/waymark/services/lifecycle.py reopen and src/waymark/services/check.py`: the messages nest double quotes around the wm reopen command, which is hard to read and to copy
- 2026-11-20 (reopened) 2.1 by planner for Noah Roberts
- 2026-11-20 (ticked) 2.1 by planner for Noah Roberts
- 2026-11-20 (review) changes 2.1; covers 1.1, 1.2, 1.3, 2.1, 2.2 by reviewer: The earlier finding is only partly fixed. wm-update still stops once acceptance is withdrawn, and wm-apply checks for a revised ticked item only under Step apply, which never comes up when every item is ticked, so no skill reliably reopens the item. 1.1, 1.2, 1.3 and 2.2 hold, and every check passes.
  - [critical] `src/waymark/assets/skills/wm-apply/SKILL.md Step apply`: the step that runs wm check and reopens each item it flags as revised-ticked-item sits only under Step `apply`, which is never reached when every item is ticked (`_item_step` returns `review`, or `archive` when an earlier pass covers every item), so a revised ticked item goes to review or archive without being reopened and 2.1's criterion does not hold; move this check before the step is chosen (wm-apply step 1, so it runs for the `review` and `archive` steps too) or into wm-update after acceptance
  - [critical] `src/waymark/assets/skills/wm-update/SKILL.md When to stop and Show the human`: step 5 says to reopen once the human has accepted again, but When to stop still says "Acceptance was withdrawn: summarize and stop" and Show the human doesn't mention reopening, so the skill ends before the reopen it tells the planner to do; the earlier review asked for both sections to change
  - [warning] `src/waymark/services/check.py _revised_ticked_findings`: an item `(resolved)` record still clears a pending warning, while the requirement names only later `(ticked)` or `(reopened)` records, and no test covers this (carried over from the earlier review)
  - [suggestion] `src/waymark/services/lifecycle.py reopen and src/waymark/services/check.py`: the messages still nest double quotes around the wm reopen command, which is hard to read and to copy
- 2026-11-20 (resolved) by Noah Roberts: wm instructions makes reopening a revised ticked item the next step before review or archive, and wm archive refuses until it is reopened; the acceptance delta names an item (resolved) too; reopen 2.1 and 2.2 for the skill and docs wording
- 2026-11-20 (revised) specs/review, specs/acceptance, design, 1.4, 2.1, 2.2 by planner for Noah Roberts: wm itself asks for the reopen, as the human decided on the second review
  - wm instructions makes reopening a revised ticked item the next step; wm archive refuses until it is done
  - the warning's requirement names an item (resolved) too
  - added 1.4 for the code; 2.1 and 2.2 now describe what wm does
- 2026-11-20 (accepted) fingerprint 55b9d54abe405029 items 1.1, 1.2, 1.3, 1.4, 2.1, 2.2 by Noah Roberts
- 2026-11-20 (ticked) 1.4 by planner for Noah Roberts

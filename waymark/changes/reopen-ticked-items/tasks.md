# Tasks

## 1. Reopening

- [ ] 1.1 Reopen any ticked item with a reason
  - **Build:** planner
  - **Criteria:**
    - `(reopened)` reads and renders with or without a reason after a colon
    - `wm reopen <change> <item> --reason "<why>"` reopens a ticked item of an accepted change that no open review names, takes its tick off and writes `(reopened) <item>` with the reason, keeping the acceptance
    - without `--reason` such an item is refused naming `--reason`; an unticked item and an unaccepted change are refused; an item a review names reopens as before, `--reason` optional
  - **Verify:** tests named after the scenarios Ticked item reopened with a reason, No reason given, Item not ticked and Reopened with a reason, and the existing reopen tests
- [ ] 1.2 Review a reopened item again
  - **Build:** planner
  - **Criteria:**
    - a passing review covers an item only when no `(reopened)` record for it follows the review
    - an item reopened after a pass and ticked again makes the next step a review of that item only, and `wm archive` refuses the change until one passes
  - **Verify:** tests named after the scenarios Item reopened after a pass, Item added after a pass and Archive before the added item is reviewed
- [ ] 1.3 Warn about a revised item left ticked
  - **Build:** planner
  - **Criteria:**
    - `wm check` warns, naming the item and `wm reopen`, when a `(revised)` record names an item that its Log shows ticked then, and no later `(ticked)` or `(reopened)` record for it follows
    - it says nothing once the item is reopened or ticked again, nor when the item wasn't ticked at the revision
  - **Verify:** tests named after the scenarios Revised item still ticked, Revised item reopened and Revised item not yet ticked

## 2. Skills and docs

- [ ] 2.1 Teach the skills to reopen
  - **Build:** planner
  - **Criteria:**
    - `wm-update` reopens each ticked item a revision changes, with `--reason`
    - `wm-apply`'s `resolve-items` step reopens the items the human's decision on an escalated review names, after recording the decision
  - **Verify:** `tests/test_skills.py` and the full pytest run
- [ ] 2.2 Update the docs and CHANGELOG
  - **Build:** planner
  - **Criteria:**
    - `docs/record.md` and `docs/concepts.md` describe `wm reopen --reason`, a reopened item's review and the `revised-ticked-item` warning
    - `CHANGELOG.md` under `## [Unreleased]` carries the User-visible lines
    - the generated docs are regenerated
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks

## Log

- 2026-11-20 (accepted) fingerprint 129122ca3ad7b588 items 1.1, 1.2, 1.3, 2.1, 2.2 by Noah Roberts

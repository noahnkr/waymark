# Reopen ticked items

- **Owner:** Noah Roberts
- **Review:** independent

## Why

A ticked item can only go back to apply when an open review names it in a `changes` verdict. Two cases need it and can't:

- **A decision on an escalated review.** After a second `changes` verdict, the human's `wm resolve <change> review` closes what the request named. When the decision is to rebuild an item, nothing reopens it. In `list-record-details`, item 2.3 got a new criterion after such a decision and was built while it stayed ticked.
- **A revision of a ticked item.** When `wm-update` changes the criteria of an item that is already ticked and the human accepts again, the item stays ticked, though its new criteria were never built against. Nothing points back at it.

In both, the record shows an item as done when it isn't.

## What changes

- **Reopen any ticked item.** `wm reopen <change> <item>` reopens a ticked item of an accepted change even when no review names it, given `--reason "<why>"`. The `(reopened)` record carries the reason as its text. When a review names the item, `--reason` stays optional, as today.
- **Reviewed again.** An item reopened after a passing review that covered it is, once ticked again, covered by no passing review, so the change gets a review of that item only, at its level, as an added item does.
- **A forgotten reopen is reported.** `wm check` warns when a `(revised)` record names an item that was ticked then, and no later `(ticked)` or `(reopened)` record for it follows.
- **Skills.** `wm-update` reopens each ticked item a revision changes. `wm-apply` reopens the items the human's decision on an escalated review names.

## Non-goals

- Unticking an item by itself when its definition changes.
- Letting an implementer or a reviewer reopen an item.
- Reopening an item of a change that isn't accepted, or one that isn't ticked.
- Changing how a `changes` verdict reopens the items it names.

## Impact

- **Specs:**
  - `review` (modified)
  - `records` (modified)
  - `acceptance` (modified)
- **User-visible:**
  - `wm reopen` reopens any ticked item with `--reason`, and the `(reopened)` record may carry a reason.
  - A reopened item gets a review of its own once it is ticked again.
  - `wm check` warns about a revised item left ticked.
- **Code:** the `(reopened)` kind in `record/evidence/records.py`, `reopen` in `services/lifecycle.py` and `cli.py`, the review state in `record/state.py`, a check in `services/check.py`, the `wm-update` and `wm-apply` skills, the docs and CHANGELOG.

## Outcome

- **Built:**
  - wm reopen <change> <item> --reason reopens any ticked item of an accepted change, and the (reopened) record carries the reason.
  - A review no longer covers an item reopened after it, so the item gets a review of its own.
  - When a revision changes a ticked item, wm instructions makes its reopen the next step, wm archive refuses even with --override, and wm check warns as revised-ticked-item.
  - The skills follow that step; the docs and CHANGELOG match.
- **Differs:**
  - Item 2.1 took two review rounds because skill wording kept missing the all-ticked case; the human's decision on the second review moved the rule into wm instructions and wm archive, added item 1.4, and named an item (resolved) in the warning's spec.
  - The third review found a crash when a revised ticked item is removed; it was fixed with a test, and the fourth review passed.
  - 2.1 and 2.2 were reopened and rebuilt through the change's own new step.
  - Three suggestions are left open: design step 6's wording, the warning's offer to tick again, and nested quotes in the messages.

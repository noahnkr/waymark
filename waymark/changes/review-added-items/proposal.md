# Review added items

Owner: Noah Roberts
Path: short

## Why

A change counts as reviewed once its last review passed and every item is ticked. An item added after that review, which the acceptance allows, is built and ticked without anyone reviewing it: `wm` goes straight to archive. On `standardize-record-lines`, item 2.3 was added after the independent review passed, and `wm` refused to start the reviewer because the change "already has the review it needs". A read-only review outside the record had to stand in.

Reviewing the whole change again would repeat work. The items that passed don't need it, only the ones added since.

## What changes

- **A review names the items it covers.** `wm review` and `wm verdict` write `covers <item>...` on the record, listing the items the review was of, such as `(review) 2026-11-20 pass covers 1.1 1.2 2.1 by wm-reviewer: <reasons>`. A review record without `covers`, written before this change, covers every item.
- **Items no passing review covers need a review of their own.** Once they are ticked, `wm instructions` makes the next step a review of those items only, at the change's level. The record it writes covers just them.
- **The reviewer gets those items.** For such a review, `wm context <change> --for review` holds the items to review with their criteria, plus the deltas, the design and the earlier reviews, and the delegation gate lets the reviewer start.
- **The archive gate** refuses a change with an item no passing review covers, as it refuses an unreviewed change, with the same override.
- **Skills and docs** say that adding an item after a review means a review of that item.

## Non-goals

- Reviewing the whole change again when an item is added.
- Covers for a `changes` verdict's reopened items: a reopened item already needs a new review.
- Changing review levels, or the escalation rules.

## Impact

- Spec `review`: a requirement is added, "Review of items added after a review".
- **Behavior change for every user, for the changelog:** review records gain `covers <item>...`; an item added after a passing review needs its own review before archive.
- Code: `record/records.py` (the `covers` arguments), `record/state.py` (the items to review), `services/lifecycle.py`, `services/context.py`, `services/instructions.py`, `hooks/decide.py` (the delegation gate), `views/`.
- Assets: `wm-apply`, `wm-update`, `wm-reviewer`. Docs: concepts.

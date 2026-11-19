# Tasks

## 1. Review the items no review covers

- [x] 1.1 Record what a review covers, and find the items no passing review covers
  - **Criteria:** `(review)` and `(self-review)` records take `covers <item>...` before `by`, and a record without it covers every item; `wm review` and `wm verdict` write every item of the change, or for a review of added items just those; `review_state` gives the ticked items no passing review covers, and the change isn't reviewed while there are any; the archive gate names them; `wm instructions` offers a review of those items only
  - **Verify:** tests in `tests/record/` and `tests/services/` for the scenarios "Item added after a pass", "Archive before the added item is reviewed" and "Older review records"
- [x] 1.2 Start the reviewer on the added items
  - **Criteria:** `wm context <change> --for review` holds only the items to review, with the deltas, the design and the earlier reviews; the delegation gate lets the reviewer start when some ticked item has no passing review; the reviewer's verdict covers those items; `wm show` shows what each review covers
  - **Verify:** tests in `tests/services/test_agent_interface.py`, `tests/hooks/test_decide.py` and `tests/views/`

## 2. Skills and docs

- [x] 2.1 Say that an added item needs its own review
  - **Criteria:** `wm-apply`, `wm-update` and the `wm-reviewer` definition say that an item added after a review is reviewed on its own, and the reviewer reviews only the items its pack holds; concepts describes `covers`; the changelog has the line; the docs follow the `waymark-write-docs` skill
  - **Verify:** `uv run --no-sync pytest tests/adapters tests/test_docs.py`, codespell and `wm check`

## Log

- 2026-11-17 (accepted) fingerprint a9c3f8d8b312bd26 items 1.1, 1.2, 2.1 by Noah Roberts
- 2026-11-17 (accepted) fingerprint 1a05f8493f2c062d items 1.1, 1.2, 2.1 by Noah Roberts
- 2026-11-17 (self-review) covers 1.1, 1.2, 2.1 by Noah Roberts: Every criterion of 1.1, 1.2 and 2.1 holds and each scenario in the review and records deltas has a test; the items fit: the covers grammar feeds review_state, which drives the next step, the archive gate, the review pack and wm show. Full checks pass (1133 tests, ruff, mypy, codespell, docs).
  - [suggestion] `src/waymark/services/check.py`: wm check doesn't report a covers that names an item the change doesn't have; such a record is read as covering a missing item
  - [suggestion] `src/waymark/services/context.py`: the review pack's items now holds only the items to review while its version stays 2; a reader that assumed every item would see fewer, so the next release note should say so
- 2026-11-17 (gap) 1.1 by Noah Roberts: The records spec's scenarios "Reviewer's verdict" and "Explicit author" (waymark/specs/records.md) give review and self-review records without covers, such as (review) 2026-11-20 pass by wm-reviewer: <reasons>, while the review delta requires every such record to name the items it covers. The change has no delta on records, so the two disagree: records needs a MODIFIED delta for those scenarios, and Impact's Specs line needs records.
- 2026-11-17 (resolved) 1.1 by Noah Roberts: A MODIFIED delta on records rewrites the Who wrote a record scenarios with covers, and Impact names records; the change was accepted again at review level self.

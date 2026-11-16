# Tasks

## 1. Review the items no review covers

- [ ] 1.1 Record what a review covers, and find the items no passing review covers
  - Criteria: `(review)` and `(self-review)` records take `covers <item>...` before `by`, and a record without it covers every item; `wm review` and `wm verdict` write every item of the change, or for a review of added items just those; `review_state` gives the ticked items no passing review covers, and the change isn't reviewed while there are any; the archive gate names them; `wm instructions` offers a review of those items only
  - Verify: tests in `tests/record/` and `tests/services/` for the scenarios "Item added after a pass", "Archive before the added item is reviewed" and "Older review records"
- [ ] 1.2 Start the reviewer on the added items
  - Criteria: `wm context <change> --for review` holds only the items to review, with the deltas, the design and the earlier reviews; the delegation gate lets the reviewer start when some ticked item has no passing review; the reviewer's verdict covers those items; `wm show` shows what each review covers
  - Verify: tests in `tests/services/test_agent_interface.py`, `tests/hooks/test_decide.py` and `tests/views/`

## 2. Skills and docs

- [ ] 2.1 Say that an added item needs its own review
  - Criteria: `wm-apply`, `wm-update` and the `wm-reviewer` definition say that an item added after a review is reviewed on its own, and the reviewer reviews only the items its pack holds; concepts describes `covers`; the changelog has the line; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync pytest tests/adapters tests/test_docs.py`, codespell and `wm check`

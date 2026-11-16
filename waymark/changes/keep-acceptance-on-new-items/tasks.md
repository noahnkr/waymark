# Tasks

## 1. Acceptance that names its items

- [ ] 1.1 Write and read the items an acceptance covers, and fingerprint only those
  - Criteria: the acceptance line reads and writes an optional `; items: <number> <number>...` after the fingerprint, and an older line without it still parses with no problem; `change_fingerprint` with a list covers only the listed items, in the listed order, with a missing listed item fingerprinted as absent, and without a list fingerprints exactly as before; `acceptance_state` uses the line's list; `wm accept` lists every item the change has; `wm sync` keeps the line's list, or its absence; the test support writes the list as `wm accept` does
  - Verify: tests in `tests/record/test_artifacts.py`, `tests/record/test_fingerprint.py`, `tests/services/test_lifecycle.py` and `tests/services/test_archive.py` for the scenarios "Accepted item edited", "Accepted item removed", "Item added", "Accepted again" and "Older acceptance line", plus an older line whose fingerprint is unchanged

## 2. Skills and docs

- [ ] 2.1 Say that only an added item keeps acceptance
  - Criteria: `wm-update` says adding an item keeps acceptance and any other edit to what was accepted withdraws it; `wm-apply` says a spec gap or a review that needs new work may add an item without a new acceptance; concepts states the rule and shows an acceptance line with its item list; the planner runs `wm update`; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync pytest tests/adapters tests/test_docs.py`, `uv run --no-sync codespell` and `wm check`

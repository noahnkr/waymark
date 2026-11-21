# Reopen ticked items: design

## Context

- `services/lifecycle.py` `reopen(start, name, number, today, *, by)` refuses an item that isn't in `state.review.reopen`, the items a still-counted `changes` verdict names. It writes `(reopened) <item>` and takes the tick off in one Log write. `cli.py` gives it no `--reason`.
- `(reopened)` in `record/evidence/records.py` has grammar `ITEM` and no text: a record with text after a colon is refused as malformed.
- `record/state.py` derives the review state. `uncovered` holds the ticked items no passing review covers, from each review's `covers`. A review counts for an item whatever happened to the item after it.
- `services/check.py` builds `wm check`'s findings from the parsed record. Warnings such as `review-level` live there.
- The `wm-update` skill runs `wm revise` after each confirmed edit. The `wm-apply` skill's `resolve-items` step resolves an escalated review with `wm resolve <change> review`.

## Approach

1. **A reason on `(reopened)`.** `KindSpec` gains `optional_text`. `(reopened)` is the one kind that sets it: it renders `: <reason>` when the record has text, and reads a record with or without it. Its shape for messages is `YYYY-MM-DD (reopened) <item> [by <who>][: <reason>]`.
2. **Reopen.** `reopen` gains `reason: str | None = None`:
   - an item in `state.review.reopen` is reopened as today, with the reason as text when given;
   - otherwise, a ticked item of an accepted change is reopened when a reason is given, and refused with a message naming `--reason` when not;
   - an item that isn't ticked, or a change that isn't accepted, is refused.

   `cli.py` adds `--reason` to `wm reopen`.
3. **Reviewed again.** In `record/state.py`, a passing review covers an item only when no `(reopened)` record for that item comes after the review in the Log. `uncovered` then lists a reopened item once it is ticked again, so `wm instructions` asks for a review of it alone, and `wm archive` refuses until one passes. A `changes` verdict's reopen keeps its own rule, which already asks for an independent review.
4. **The warning.** `services/check.py` walks each active change's Log in order and keeps, per item, whether its latest `(ticked)`, `(reopened)` or item `(resolved)` record was a `(ticked)`. When a `(revised)` record names an item that is ticked at that point, and no `(ticked)` or `(reopened)` record for it comes later, it adds the warning `revised-ticked-item`.
5. **`wm` asks for the reopen.** The Log walk of step 4 moves into `record/state.py` as `revised_ticked(tasks)`, used by the check and by the state. `_item_step` returns, right after an escalated review, an `apply` step with a reason for the first revised ticked item. `services/instructions.py` puts `wm reopen <change> <item>` first among its commands, adding `--reason "<what the revision changed>"` when no review names the item. `_archive_gate` in `services/lifecycle.py` refuses a change with a revised ticked item, before the override is looked at.
6. **Skills and docs.** `wm-update` step 3: after a revision that changes a ticked item, run `wm reopen <change> <item> --reason "<why>"`. `wm-apply`'s `resolve-items`: when the human's decision rebuilds items, record it with `wm resolve <change> review`, then reopen each one with `--reason`. `docs/record.md` and `docs/concepts.md` describe `--reason` and the warning; the CHANGELOG says what users see; the CLI reference is regenerated.

## Decisions

### Decision: How a ticked item goes back to apply
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `wm reopen` reopens any ticked item, with a reason when no review names it
  - `wm resolve <change> review --reopen <item>...`, for an escalated review only
  - untick an item by itself when its definition changes, from per-item fingerprints
- **Choice:** `wm reopen` with a reason
- **Why:** it covers both the escalated review and a revision outside a review, and records why.

### Decision: A reopened item's review
- **Status:** decided
- **Decided by:** human
- **Options:**
  - once ticked again, it needs a review of that item only, at the change's level
  - the earlier passing review still covers it
- **Choice:** a review of that item only
- **Why:** its earlier review was of the item as it was; what was built again hasn't been checked.

### Decision: Reporting a forgotten reopen
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `wm check` warns when a `(revised)` record names a ticked item with no later `(ticked)` or `(reopened)` record
  - no check
- **Choice:** the warning
- **Why:** it uses records that already exist, and would have caught item 2.3 of `list-record-details`.

### Decision: When the reason is required
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - required when no open review names the item, optional when one does
  - always required
- **Choice:** required only when no review names the item
- **Why:** a review that names an item already says why in the Log, so asking again would repeat it.

### Decision: Knowing whether an item was ticked at a revision
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - from the Log: the item's latest `(ticked)`, `(reopened)` or item `(resolved)` record before the revision
  - from the item's checkbox as it stands now
- **Choice:** from the Log
- **Why:** the checkbox only says what is true now. The Log says what was true when the revision was written. An active change from before `(ticked)` records were written has none, so it gets no warning rather than a wrong one.

### Decision: Who makes sure a revised item is reopened
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `wm instructions` makes the reopen the next step, and `wm archive` refuses until it is done
  - the skills tell the planner to run `wm check` and reopen what it warns about
- **Choice:** `wm instructions` and `wm archive`
- **Why:** two review rounds showed the skills alone miss it: after the human accepts again with every item ticked, the next step is review or archive, which no skill wording reliably catches. `wm` already reads the case from the Log, so it can ask for the reopen itself.

## Open questions

None.

## Risks and trade-offs

- The planner can now untick any item with a reason. Only the planner can, and the reason is in the Log, but nothing checks that it is a good one.
- An item reopened after a pass needs one more review, which costs a reviewer run at level `independent`.

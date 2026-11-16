# Keep acceptance on new items: design

## Context

- **The acceptance line.** `record/proposal.py` reads the acceptance line with `_ACCEPTANCE`, `<date> by <who> (fingerprint: <16 hex>)`, into `Acceptance(date, who, fingerprint, index)`. Anything else gives `malformed-evidence`. `format_acceptance` writes the line.
- **The fingerprint.** `record/fingerprint.py` builds one part per item, `item:<number>`, from its definition, among the other parts. The digest covers every item, so appending one changes it.
- **Where it is used.**
  - `record/state.py` `acceptance_state` compares the stored fingerprint with `change_fingerprint(change, specs, default)`.
  - `services/lifecycle.py` `accept` writes the line.
  - `sync` rewrites it with the fingerprint taken against the merged specs.
  - `tests/support.py` `Workspace.accept` writes it for the tests.
- **Item numbers are never reused.** `record/tasks.py` reports an item number that is out of order or used twice, and the guidance says to append new items at the end. A number in the list therefore always means the same item.

## Approach

1. **Line format.**
   - Extend `_ACCEPTANCE` with an optional `; items: <n.n>( <n.n>)*` before the closing parenthesis.
   - Add `Acceptance.items: tuple[str, ...] | None`, which is None for an older line.
   - `format_acceptance(date, who, fingerprint, items)` writes the list when it is given. It always is now.
2. **Fingerprint.**
   - `fingerprint_parts` and `change_fingerprint` take `items: Collection[str] | None`.
   - With None, every item is covered, as today.
   - With a list, only the parts of those items are included, in the list's order. A listed number with no item in the task list gives the part `_ABSENT`, so removing an accepted item changes the digest.
   - All other parts are unchanged, so an acceptance line with no list fingerprints exactly as before.
3. **State.** `acceptance_state` passes `acceptance.items` to `change_fingerprint`.
4. **Accept and sync.**
   - `accept` lists every item number the change has, and fingerprints with that list.
   - `sync` keeps the existing list: an older line stays an older line, and a line with a list keeps it. That way syncing never brings in an item the human didn't accept.
5. **Tests and support.** `Workspace.accept` writes the list as `wm accept` does. Tests cover:
   - each scenario of the `acceptance` delta;
   - an older line that still parses and fingerprints the same;
   - the existing withdrawal tests, which now edit, remove or retag accepted items.

   The test that appends an item and expects acceptance to be withdrawn changes to expect it to stay.
6. **Skills and docs.**
   - `wm-update` says that adding an item keeps acceptance, and that any other edit withdraws it.
   - `wm-apply` says that a spec gap or a review that needs new work may add an item without a new acceptance.
   - Concepts gets the same rule, and an example acceptance line.

## Decisions

### Decision: How the acceptance knows which items it covered
- Options:
  - list the item numbers in the acceptance line;
  - a fingerprint per item;
  - treat every item numbered above the highest one at acceptance as added.
- Choice: list the item numbers in the line.
- Why: The line is what the human's approval wrote, so it should say what it covered. Per-item fingerprints would make the line long. A "highest number" rule breaks when a new section is added after the item numbering restarts.

### Decision: Added items are not marked
- Options:
  - mark added items in `wm status`, `wm show` and the pull request;
  - treat them like any other item.
- Choice: treat them like any other item (the human chose it).
- Why: An added item can't change what the system is said to do, because the deltas are covered. The change's one review checks every item, added ones too, before archive.

### Decision: Older acceptance lines
- Options:
  - migrate them with `wm update`;
  - read them as covering every item.
- Choice: read them as covering every item.
- Why: Their fingerprint was taken over every item, so that is what they cover. No change is in flight to migrate, and old archived lines keep parsing.

## Risks and trade-offs

- **Work the human didn't see before it was built.** An added item is built without the human seeing it first. The deltas bound what it can do, and the review and the pull request show it before anything is archived or merged.
- **Two formats for one line.** The parser accepts both, and `wm` only writes the new one.

# Keep acceptance on new items

Owner: Noah Roberts
Review: independent

## Why

Any edit to an accepted change withdraws its acceptance, including adding a task item. That is right when something the human approved changes. An added item, though, leaves everything approved as it was: the proposal, the deltas, the design and the existing items. Yet today it costs a round trip to the human.

Items get added for ordinary reasons: a spec gap that needs one more step, a review asking for something no item covers, or work the planner finds while building. On `drop-waymark-folder`, each added item meant the human had to accept again. The exploration `lighter-workflow` asked for acceptance to be withdrawn only when what was accepted changes. This is the fifth change on that milestone.

## What changes

- **Adding an item keeps acceptance.** A new task item appended to an accepted change can be built right away, like any other item, and nothing marks it as added later.
- **Changing what was accepted still withdraws it.** That covers the proposal, a delta, the design, the living text a delta modifies or removes, and the definition of any item that was accepted, including removing it.
- **The acceptance line names the items it covers:** `Accepted: <date> by <who> (fingerprint: <digest>; items: 1.1 1.2 2.1)`.
  - Accepting again covers every item the change then has.
  - Syncing keeps the list.
  - An acceptance line without a list, written before this change, covers every item as today.
- **`wm-update` and the docs** say that only an added item keeps acceptance.

## Non-goals

- Marking added items, or showing them apart in `wm status`, `wm show` or the pull request.
- Letting the design or an unbuilt item's criteria change without withdrawing acceptance.
- Moving the charter into config. It is the milestone's last change.

## Impact

- New spec `acceptance`: what an acceptance covers, items added after it, and acceptance lines written before items were listed.
- **Behavior change for every user, for the changelog:**
  - adding an item no longer withdraws acceptance;
  - the `Accepted:` line now lists the items it covers.

  Older lines still work, so no migration is needed.
- Code: `record/proposal.py` (the line's format), `record/fingerprint.py` (the accepted items), `record/state.py`, `services/lifecycle.py` (accept and sync), and the test support.
- Assets: `wm-update` and `wm-apply`.
- Docs: concepts.

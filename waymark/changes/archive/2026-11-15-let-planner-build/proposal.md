# Let planner build

- Owner: Noah Roberts

## Why

Every task item is built by a fresh implementer agent. Each implementer starts cold: before it does any work it reads the charter, the proposal, the deltas, the design and the nearby code. Then it runs the full checks, because the charter's apply rule says to.

On `drop-waymark-folder` that came to 8 implementer runs, about 775k tokens and about 47 minutes for small items. That is roughly 80% of what the change cost. The planner already holds this context. Most items don't need a cold agent, and in that change the cold start never turned up a spec gap. The exploration `lighter-workflow` weighs the options, and this change is the first on the milestone of the same name.

## What changes

- **The planner builds items by default.** At the apply step, `wm instructions` tells the planner to build the item itself from the item's context pack. The planner runs the tests the item touches, then ticks the item with `wm tick`.
- **A `build: delegate` tag sends an item to a fresh implementer.** Use it for large items, for items that can be built in parallel, or where a cold check that the record is enough to build from is worth its cost. The tag sits on the item line next to `review:`. It is part of what the human accepts, so changing it withdraws acceptance. For a tagged item, `wm instructions` says to start an implementer, as it does for every item today.
- **In an atlas, the planner may edit a code repo while an accepted item that is being built names it.** That is the same rule implementers follow. Elsewhere the planner still edits only the record.
- **Tests run once in full.** The charter's apply rule changes from "Run the full checks before reporting done" to: run the checks the item touches, and run the full checks once before the pull request.
- **The skills, agent definitions, docs and charter are reworded.** "Code is always built by an implementer" becomes "the record is the source of truth". `wm-apply`, `wm-propose`, `wm-onboard`, concepts, getting started, the multi-repo guide, the smoke test, the README and the charter's vision all change to match.

## Non-goals

- Changing how items are reviewed. Per-item `self`, `independent` and `none` stay. The `review-per-change` change on the milestone takes that up.
- Forcing a tagged item to be delegated. The hooks can't see which item a planner edit belongs to, so the tag guides `wm instructions` and the skills, and isn't a gate.
- Archiving before the merge, the tiny path, and moving the charter into config. These are later changes on the milestone.

## Impact

- New spec `building`: the planner builds by default, a tag sends an item to an implementer, and the rule for planner edits in an atlas.
- **Behavior change for every user, for the changelog:**
  - `wm instructions` at the apply step tells the planner to build the item unless the item is tagged `build: delegate`;
  - the task list format gains the `build: delegate` tag;
  - in an atlas, the hooks let the planner edit an accepted item's code repo.
- Code: `record/tasks.py` (the tag), `record/fingerprint.py` (the tag becomes part of what is accepted), `services/instructions.py`, `hooks/decide.py`, and the item templates and JSON schema in `views/`.
- Assets: the `wm-apply`, `wm-propose`, `wm-onboard` and `wm-update` skills, and the `wm-implementer` definition.
- Docs: concepts, getting started, the multi-repo guide, the smoke test, architecture, the README and the regenerated CLI and JSON references. The charter's vision and its apply rule change too.

## Outcome

The planner now builds task items itself by default: wm instructions at the apply step tells it to build an untagged item from its context pack, run the checks the item touches and record the result with wm tick, wm block or wm gap, while an item tagged build: delegate still goes to a fresh implementer. The tag is read in either order with review:, is part of what is accepted (added to the fingerprint only when present, so existing acceptances survive an upgrade), and in an atlas the planner may edit the code repo of the item being built. The skills, charter (vision, first goal and apply rule) and docs were reworded to match; the charter edits were made by the planner because implementers may not edit it, and the planner ran wm update for item 2.1 for the same reason.

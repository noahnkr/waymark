# Name build roles: design

## Context

- `record/artifacts/tasks.py` reads the Build line into two fields on `Item`: `delegate: bool`, true for `delegate`, and `build: str | None`, the value when it is one of `BUILD_VALUES = (PLANNER, DELEGATE)`. Unknown values are reported as `unknown-build-tag`, and `record/artifacts/changes.py` names the two values when the line is missing.
- `services/instructions.py` picks the apply guidance with `built.build == DELEGATE`, and the tasks step's guidance names `planner` and `delegate`.
- `services/context.py` holds the delegation gate (`_item_problem`), which the hook calls when an implementer is started. It doesn't look at the Build line. `_definition` builds each item for the implement and review packs, without its role.
- `views/payloads.py` puts `"delegate": item.delegate` on each item of `wm show --json` (`show.change`, version 3). `views/render.py` shows the tag `build: delegate`, and `views/schemas.py` declares the field.
- `hooks/events.py` has a `Role` (planner, implementer, reviewer) for whoever is acting in a session. That is a different idea from the role an item names, and stays as it is.
- The tasks template, the skills (`wm-propose`, `wm-apply`), the agent definitions, `docs/` and the README name `planner` and `delegate`. 11 archived task lists hold `- **Build:** delegate`.

## Approach

1. **Roles.** Add `BuildRole` (`planner`, `implementer`, `human`) to `record/terms.py`. `Item` gets `build: BuildRole | None` in place of `delegate` and the string `build`. The parser reads the three values, and reports any other value (`delegate` included) and a missing line naming all three. Every reader of `item.delegate` asks `item.build is BuildRole.IMPLEMENTER`.
2. **Apply guidance.** `_working` picks one of three guidance blocks from the role:
   - `implementer` keeps today's text;
   - `planner` keeps today's text;
   - `human` tells the planner to show the human the item's Criteria and Verify as the steps, to run `wm tick` only after their yes, and to `wm block` the item with what it waits on when they can't do it now. Its commands are `wm tick` and `wm block`, and there is no `wm context` command for it.
3. **Delegation gate.** `_item_problem` refuses an item whose role is `human`, saying the human does it and the planner ticks it after their yes. The hook already calls the gate, so it refuses the implementer.
4. **Review.** `_definition` adds `build` to each item in the implement and review packs. The review pack and the review step's guidance add a sentence that names the `human` items, if there are any, and says their ticks are the human's confirmation, while what they left in the repo is still checked. `DELEGATED_VERSION` goes to 3.
5. **Views.** `wm show --json` gives `"build"` (the role, or null without a known value) in place of `"delegate"`. `show.change` goes to version 4, and the schema is updated. The text view shows `build: implementer` or `build: human` and nothing for `planner`, as it shows nothing for `planner` today.
6. **Record and assets.** The tasks template's example says `implementer`. Its comment names the three roles. The skills, the agent definitions and the docs use the roles, and keep "delegate" only as the verb. The archive's 11 lines are changed by hand in the docs item.

## Decisions

### Decision: How an item holds its role
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - one `BuildRole` enum in place of `delegate` and the string `build`
  - keep `delegate` and add a `human` flag next to it
- **Choice:** one `BuildRole` enum
- **Why:** an item has exactly one role. Two flags could both be true, and every reader would have to know which one wins.

### Decision: Where a human item waits
- **Status:** decided
- **Decided by:** human
- **Options:**
  - the planner blocks it with `wm block`, naming what it waits on, and `wm resolve` lifts the block
  - a new state for an item that waits on the human
- **Choice:** `wm block`
- **Why:** a blocked item already lets the change go on with the next item and shows in `wm inbox`, so no new state or command is needed.

### Decision: How a review learns about human items
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - add each item's role to the packs, and a sentence that names the human items
  - only a sentence in the guidance
- **Choice:** the role in the packs, and the sentence
- **Why:** a reviewer reads the pack as data. With the role on each item it can tell a human item from the rest without parsing prose, and the sentence says what to do about it.

### Decision: The JSON field
- **Status:** decided
- **Decided by:** human
- **Options:**
  - replace `delegate` with `build`, and raise the schema version
  - keep `delegate` and add `build` next to it
- **Choice:** replace it, and raise the version
- **Why:** there are no other users to keep compatible, and two fields saying the same thing could disagree.

### Decision: The archived task lists
- **Status:** decided
- **Decided by:** human
- **Options:**
  - change the 11 lines once, by hand
  - read `delegate` as an old spelling of `implementer`
- **Choice:** by hand, once
- **Why:** this record is Waymark's only instance, so code to read the old value would only ever run on these 11 lines.

## Open questions

None.

## Risks and trade-offs

- An active change elsewhere with `- **Build:** delegate` would stop checking clean. There are none here, and the CHANGELOG says to change the value.
- The planner ticks a `human` item, so until the change to the Log's authorship, nothing in the record says the human confirmed it. Only the planner's word in the session stands for it.
- Raising `show.change` and the packs' versions breaks any script that reads `delegate`. None is known.

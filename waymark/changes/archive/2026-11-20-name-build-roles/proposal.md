# Name build roles

- **Owner:** Noah Roberts
- **Review:** independent

## Why

A task item's `- **Build:**` line says who builds it, but its two values take different points of view. `planner` names a role, while `delegate` is something the planner does. Read by an implementer, `delegate` describes the implementer from the outside, and `planner` is someone else. The record should name the same role whoever reads it.

Some work in a change can only be done by the human: filling in a form, a manual test, setting up a platform or an account. Today such work has no kind of item. The planner either writes it as an item it can't build, or blocks the item with `wm block` and waits for `wm resolve`. Either way, `wm instructions` says nothing about handing the work to the human.

## What changes

- The Build line takes one of three roles: `planner`, `implementer` or `human`. `implementer` replaces `delegate`, and `wm check` reports any other value, `delegate` included, naming the three.
- When the next item to apply is `human`, `wm instructions` tells the planner to show the human the item's Criteria and Verify as the steps to take, and to wait for their yes before ticking it. If the human can't do it now, the planner blocks the item with what it waits on, so the change can go on with its other items.
- An implementer started on a `human` item is refused, with a reason saying the human does it.
- A review takes the tick of a `human` item as the human's confirmation of what only they could check. It still checks anything the item left in the repo, such as a resource.
- `wm show --json` gives each item `"build": "planner" | "implementer" | "human"` in place of `"delegate": true | false`, and the view's schema version goes up. The text view shows the role for `implementer` and `human` items.
- The 2 archived task lists with `- **Build:** delegate` are changed to `implementer` once, by hand. No migration code is added.
- The skills, the agent definitions and the docs use the three roles. "Delegate" stays only as the verb for handing an item to an implementer.

## Non-goals

- Recording who ticked an item. A `(ticked)` record, with your name on a `human` item, comes with the change to the Log's authorship.
- Changing who writes records today, or how they name who wrote them.
- Reading `delegate` as an old spelling of `implementer`.
- Letting the human tick an item with their own command. The planner ticks it after their yes.

## Impact

- **Specs:**
  - `building` (modified)
  - `authored-formats` (modified)
  - `formatting` (modified)
  - `review` (modified)
- **User-visible:**
  - The Build line's values are `planner`, `implementer` and `human`; `delegate` is reported as an unknown value.
  - `wm instructions` hands a `human` item to the human.
  - An implementer started on a `human` item is refused.
  - `wm show --json` has `build` in place of `delegate` on each item, at a new schema version.
  - The skills, the agent definitions and the docs name the three roles.
- **Code:** the task list parser in `record/artifacts/tasks.py` and its check in `record/artifacts/changes.py`, the apply and review guidance in `services/instructions.py`, the delegation gate in `services/context.py`, the views in `views/payloads.py`, `views/render.py` and `views/schemas.py`, the tasks template, the skills and agents in `assets/`, the docs and CHANGELOG, and the archived task lists.

## Outcome

- **Built:** An item's Build line names a role, planner, implementer or human, and delegate is reported as unknown. A human item is handed to the human with its steps, ticked after their yes, and blocked while it waits, and an implementer started on one is refused. The review pack and review guidance name the human's items. wm show --json gives each item build (show.change version 4), and the packs carry it (version 3). The skills, agent definitions, docs, README, CHANGELOG and the 2 archived task lists use the roles.
- **Differs:** The first independent review asked for changes to 2.2 because the README didn't name the roles; that was fixed with the reviewer's wm-onboard wording, and the second review passed. Item 2.2 was corrected during the build from 11 archived task lists to 2, since the count had included archived proposals and deltas that keep the old wording as history, and the change was accepted again. One review suggestion on the README's wording is left open.

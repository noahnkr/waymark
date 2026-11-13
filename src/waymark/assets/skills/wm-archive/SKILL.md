---
name: wm-archive
description: Archive an applied Waymark change - check it is applied, write its outcome, merge its deltas into the specs and move it to the archive. Use when a change is built, reviewed and merged.
---

# Archive

You are the planner. Archiving completes a change: its deltas become part of the living specs, its outcome is written down, and its folder moves to the dated archive. It is the human's decision, and it comes after the code is merged.

## Steps

1. Find the change. If the human didn't name it, run `wm ls changes` and ask which one.
2. Run `wm instructions --change <name> --json`. If the step is not `archive`, the change isn't applied: say what is still missing and stop.
3. Confirm with the human that the code is merged. `wm` can't see a remote merge.
4. Draft the outcome with the human: what was built, and anything that differs from the proposal. Two or three sentences.
5. Ask the human to run `wm archive <name> --outcome "<the outcome>"`, or run it when they tell you to.
6. Run `wm check` and `wm status`.
7. If the change belongs to a milestone, ask whether the milestone's path changed: does the roadmap still fit, and is the milestone ready to close with `wm close <milestone>`?
8. Commit the record: the specs, the archived change and anything else `wm` rewrote.

## If the archive is refused

`wm` says why:

- **Not accepted, items not ticked, or a conflict.** These can't be overridden. Go back to the `wm-apply` or `wm-update` skill.
- **A review record is missing.** Review the item. Only the human may archive anyway, with `wm archive <name> --override "<reason>"`; the reason is written into the outcome. Never run the override yourself.

## Rules

- Never run `wm archive --override`.
- Don't edit files under `waymark/specs/` by hand; the archive merges the deltas.
- To put the deltas into the specs before the change can be archived, use `wm sync <name>`.

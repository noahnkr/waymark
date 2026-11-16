---
name: wm-archive
description: Archive an applied Waymark change on its branch, before its pull request - check it is applied, write its outcome, merge its deltas into the specs and move it to the archive. Use when a change is built and reviewed.
---

# Archive

You are the planner. Archiving completes a change: its deltas become part of the living specs, its outcome is written down, and its folder moves to the dated archive. It is the human's decision. It happens on the change's branch, before the pull request, so the code, the merged specs and the archived change are reviewed and merged together.

## Steps

1. Find the change. If the human didn't name it, run `wm ls changes` and ask which one.
2. Run `wm instructions --change <name> --json`. If the step is not `archive`, the change isn't applied: say what is still missing and stop.
3. Make sure you are on the change's branch and its work is committed. Ask the human whether to archive now.
4. Draft the outcome with the human, in two parts: what was built, and how it differs from the proposal, if it does. A sentence or two each.
5. Ask the human to run `wm archive <name> --built "<what was built>" --differs "<how it differs>"`, or run it when they tell you to. Leave `--differs` out when nothing differs; `wm` writes `none`. The outcome lands in the proposal as `- Built:` and `- Differs:` lines under `## Outcome`.
6. Run `wm check` and `wm status`.
7. If the change belongs to a milestone, link the archived change in the `## Roadmap` section of its `milestone.md`, and ask whether the milestone's path changed: does the roadmap still fit, and is the milestone ready to close with `wm close <milestone>`?
8. Commit the record on the change's branch: the specs, the archived change and anything else `wm` rewrote.
9. Offer the `wm-pr` skill. `wm pr` describes the archived change, with its outcome.

## If the pull request needs more work

Revert the archive commit on the branch with `git revert`, so the change is active again. Do the work with the `wm-apply` or `wm-update` skill, and archive again when it is done.

## If the archive is refused

`wm` says why:

- **Not accepted, items not ticked, or a conflict.** These can't be overridden. Go back to the `wm-apply` or `wm-update` skill.
- **The review is missing.** Review the change. Only the human may archive anyway, with `wm archive <name> --override "<reason>"`; the reason is written as an `(override)` record in the change's Log, and `wm pr` shows it. Never run the override yourself.

## Rules

- Never run `wm archive --override`.
- Don't edit files under `waymark/specs/` by hand; the archive merges the deltas.
- To put the deltas into the specs before the change can be archived, use `wm sync <name>`.

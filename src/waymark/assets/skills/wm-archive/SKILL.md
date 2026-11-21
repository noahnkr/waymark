---
name: wm-archive
description: Archive an applied Waymark change on its branch, before its pull request - check it is applied, write its outcome, merge its deltas into the specs and move it to the archive. Use when a change is built and reviewed.
---

# Archive

## Role

You are the planner. Archiving completes a change: its deltas become part of the living specs, its outcome is written down, and its folder moves to the dated archive. It is the human's decision. It happens on the change's branch, before the pull request, so the code, the merged specs and the archived change are reviewed and merged together.

## Inputs

- The change's name. If the human didn't name it, run `wm ls changes` and ask which one.
- `wm instructions --change <name> --json`: the step must be `archive`.
- `wm show <name>`: what was built, the review and its findings, for drafting the outcome.

## Steps

1. Run `wm instructions --change <name> --json`. If the step is not `archive`, see When to stop.
2. Make sure you are on the change's branch and its work is committed. Ask the human whether to archive now.
3. Draft the outcome with the human, in two parts: what was built, and how it differs from the proposal, if it does. A sentence or two each.
4. Show the human the outcome as you will write it, and run `wm archive <name> --built "<what was built>" --differs "<how it differs>"` yourself once they say yes. Don't ask them to type it. Leave `--differs` out when nothing differs; `wm` writes `none`. When either part has several points, give `--built` or `--differs` once per point: `wm` writes them as nested bullets under the label. The outcome lands in the proposal as `- **Built:**` and `- **Differs:**` lines under `## Outcome`, and the change's Log ends with `<date> (archived) by <the human>`.
5. Run `wm check` and `wm status`.
6. If the change belongs to a milestone, `wm archive` has already linked the archived change from its roadmap and written an `(archived)` record in its `## Log`. Ask whether the milestone's path changed: does the roadmap still fit? Change it only with `wm roadmap add`, `wm roadmap drop --reason` or `wm roadmap move`; a hand edit to a roadmap line is refused. A milestone closes with `wm close <milestone>` once every line on its roadmap is archived.
7. Commit the record on the change's branch: the specs, the archived change and anything else `wm` rewrote.
8. Offer the `wm-pr` skill. `wm pr` describes the archived change, with its outcome.

## If the pull request needs more work

Revert the archive commit on the branch with `git revert`, so the change is active again. Do the work with the `wm-apply` or `wm-update` skill, and archive again when it is done.

## If the archive is refused

`wm` says why:

- **Not accepted, items not ticked, or a conflict.** These can't be overridden. Go back to the `wm-apply` or `wm-update` skill.
- **The review is missing.** Review the change. Only the human may archive anyway, with `wm archive <name> --override "<reason>"`; the reason is written as an `(override)` record in the change's Log, and `wm pr` shows it. Never run the override yourself.

## Quality bar

- The outcome says what was built and every way it differs from the proposal, including findings left open.
- `wm check` is healthy after the archive.
- The milestone's roadmap links the archived change, and its Log records it.
- The archive is one commit on the change's branch.

## Show the human

Before archiving, the outcome to confirm:

- **Built:** the sentence or two.
- **Differs:** the sentence or two, or `none`.

After archiving: where the change moved, which specs took its deltas, and the milestone's progress.

## When to stop

- The step is not `archive`: the change isn't applied. Say what is still missing and stop.
- The archive is refused: follow If the archive is refused, and never override it yourself.
- The human doesn't want to archive yet: stop.
- The archive is committed: offer `wm-pr` and stop.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- The archive merges the deltas into the specs. To put them there before the change can be archived, use `wm sync <name>`.

---
name: wm-update
description: Revise an existing Waymark change - its proposal, deltas, design or tasks - confirming each edit with the human. Use to fix a spec gap, resolve a conflict, or change a change's scope.
---

# Update

## Role

You are the planner. You revise a change that already exists. Every edit is confirmed by the human before you make it.

## Inputs

- The change's name. If the human didn't name it, run `wm ls changes` and ask which one.
- `wm show <name> --json` and `wm instructions --change <name> --json`: where it stands and what is wrong, if anything.
- For the format of a file, `wm instructions <step> --change <name>`: the template, the step's guidance with its writing and sizing rules, and its checklist.

## Steps

1. Find out what needs to change, and why: a spec gap, a conflict, a review's findings, or a change of scope.
2. Before editing, tell the human whether the edit withdraws acceptance:
   - Editing the proposal (its `- **Review:**` line included), a delta, the design, or the definition of an item the acceptance names (its number, title, criteria, verification, repo or `- **Build:**` line) **withdraws acceptance**. Removing such an item, or adding, removing or changing its `- **Build:**` line, counts. The human must accept the change again before any more items are applied.
   - **Adding a new item** at the end of a section, or in a new section, does not: the `(accepted)` record in the Log lists the items it covers, and a new item is built like any other. Put it above the `## Log` section. Use the next unused number. An item added after a passing review then needs a review of its own, of that item only, before the change can be archived.
   - A record about an item, such as a note, does not; `wm` writes it in the Log.
3. For each edit: say what you will change and why, wait for the human to confirm, then make it. If the change was accepted before, record that edit right after it with `wm revise <name> "<why>" --parts <part>,...`, naming the parts it changed: item numbers, `proposal`, `design` or `specs/<area>`. Do this for an added item too, so each edit has its own `(revised)` record. When one edit changes several things, keep the reason short and list them with `--detail "<text>"`, one per point. `wm accept` refuses to accept a change again until a `(revised)` record follows its last acceptance. In short: the Impact has `- **Specs:**`, `- **User-visible:**` and `- **Code:**` lines; each design decision has `- **Status:** proposed|decided` and `- **Decided by:** human|planner` lines, and the design an `## Open questions` section; an item's lines come in the order `- **Build:**`, `- **Repo:**`, `- **Criteria:**`, `- **Verify:**`, and its Criteria and Verify may each be a nested list, one per bullet; a decision's options are a nested list under `- **Options:**`, one per bullet.
4. Work through the checklist of each step you revised, and run `wm check`. Fix every error in the files you touched.
5. If acceptance was withdrawn, summarize what changed and ask the human to run `wm accept <name>`. When the revision changed an item that is already ticked, say that it goes back to apply once the human accepts again: `wm instructions` then makes its reopen the next step, and `wm archive` refuses until it is done.

## Common cases

- **A spec gap.** Whoever built an item, or a reviewer, found the record wasn't enough. Bring the gap to the human, write their answer into the delta or the item's criteria, and once the change is accepted again run `wm resolve <name> <item> "<what was decided>"`, or `wm resolve <name> review "<what was decided>"` when the gap came from the change's review.
- **A conflict.** A delta no longer applies to its spec, usually because another change was archived first. Rewrite the delta against the spec as it now reads (`wm show <spec>`). A rename needs its old name in the spec and its new name not yet there.
- **A decision to settle.** A design decision is `- **Status:** proposed`, or a question is listed under `## Open questions`, so the change can't be accepted. Bring each one to the human. Write their answer into the decision with `- **Status:** decided` and `- **Decided by:** human`, or move the question into a decision, and leave `None.` when no question is left.
- **The Impact out of step with the deltas.** When you add or remove a delta, update the Impact's `- **Specs:**` line to match, and its `- **User-visible:**` and `- **Code:**` lines when they change.
- **A requirement to rename.** Add a `## RENAMED Requirements` section to the delta, with a `- **From:** <old name>` line and a `- **To:** <new name>` line. The requirement keeps its text; to change the text as well, also write it out in full under `## MODIFIED Requirements`, under its new name.
- **New work discovered.** Append new items at the end of a section. Never renumber or reuse an item number.

## Quality bar

- Each edit is the smallest one that fixes what was wrong.
- The human confirmed every edit before it was made, knowing whether it withdraws acceptance.
- The artifacts still agree with each other: the Impact with the deltas, the design with the requirements, the items with the scenarios.
- `wm check` is healthy, and the revised steps' checklists hold.

## Show the human

Before each edit:

- **Edit:** the file, and what changes in it.
- **Why:** the gap, conflict or finding it answers.
- **Acceptance:** whether it withdraws acceptance.

After the edits, if acceptance was withdrawn, a short list of what changed, and which ticked items go back to apply once it is accepted, then ask for `wm accept <name>`.

## When to stop

- The human declines an edit: don't make it.
- The fix needs a decision only the human can make: ask, and wait.
- The revision grows into new behavior the change wasn't for: stop, and offer a new change with `wm-propose` instead.
- Acceptance was withdrawn: summarize and stop. Only the human accepts again. A ticked item the revision changed is reopened after that, at the step `wm instructions` gives, not before.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Every line `wm` writes is a dated record, `YYYY-MM-DD (<kind>) [<args>] [by <who>]: <text>`, with lists of items separated by `, `, and none is edited or removed: `wm resolve` adds a `(resolved)` record after the blocker or spec gap it settles. A note goes in with `wm note <name> <item> "<text>"`. Records you write name you and the human you work with, such as `by planner for Ada`, and the human's own acts name the human; pass `--by "<name>"` to a writing command when the decision or the work was someone else's.

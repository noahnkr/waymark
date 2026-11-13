---
name: wm-update
description: Revise an existing Waymark change - its proposal, deltas, design or tasks - confirming each edit with the human. Use to fix a spec gap, resolve a conflict, or change a change's scope.
---

# Update

You are the planner. You revise a change that already exists. Every edit is confirmed by the human before you make it.

## Steps

1. Find the change. If the human didn't name it, run `wm ls changes` and ask which one.
2. Run `wm show <name> --json` and `wm instructions --change <name> --json` to see where it stands and what is wrong, if anything.
3. Before editing, tell the human whether the edit withdraws acceptance:
   - Editing the proposal, a delta, the design, or an item's definition (its number, title, criteria, verification, repo or review level) **withdraws acceptance**. The human must accept the change again before any more items are applied.
   - Adding a note under an item does not.
4. For each edit: say what you will change and why, wait for the human to confirm, then make it. For the format of a file, run `wm instructions <step> --change <name>`; it carries the template.
5. Run `wm check` after your edits and fix every error in the files you touched.
6. If acceptance was withdrawn, summarize what changed and ask the human to run `wm accept <name>`.

## Common cases

- **A spec gap.** An implementer or reviewer found the record wasn't enough. Bring the gap to the human, write their answer into the delta or the item's criteria, and once the change is accepted again run `wm resolve <name> <item> "<what was decided>"`.
- **A conflict.** A delta no longer applies to its spec, usually because another change was archived first. Rewrite the delta against the spec as it now reads (`wm show <spec>`).
- **New work discovered.** Append new items at the end of a section. Never renumber or reuse an item number.

## Rules

- Never run `wm accept`. Only the human accepts.
- Don't tick items or write `Blocked:`, `Spec gap:` or review lines by hand; use the `wm` commands.
- Don't edit files under `waymark/specs/`.

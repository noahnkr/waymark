# Add step guidance

- Owner: Noah Roberts

## Why

`wm instructions` tells the planner what to do at each drafting step, but not what must hold before it moves on, and not which of those things `wm check` will catch for it. The planner either re-derives the quality bar from the skill, or trusts `wm check` for things it doesn't check, such as a THEN nobody else could verify.

The rules every skill shares (only the human accepts, only `wm` writes records, specs aren't edited by hand, ask instead of guessing, nothing is pushed without a yes) are copied into the nine skills with slightly different wording, so they drift.

Two gaps in `wm check` let weak drafts through: a task item without criteria or a way to verify it, and a design decision with one option.

This is the fifth change on the `record-format-and-skills` milestone.

## What changes

- **Checklist:** for each drafting step (propose, specs, design, tasks), `wm instructions` gives a checklist next to "What to do": what must hold before moving on. Each check says whether `wm check` enforces it.
- **Shared rules:** every `wm instructions` output starts from one list of the rules every skill shares. The skills drop their copies of those rules and keep only their own.
- **Two new checks** for active changes: a task item needs a `- Criteria:` line and a `- Verify:` line, and a design decision needs at least two options.
- **Skills and docs** point at the shared rules and the checklist.

## Non-goals

- One layout for every skill, writing rules for requirements, sizing rules and the reviewer's severity rubric: `sharpen-drafting-skills`.
- Checklists for the steps that work on an accepted change (apply, review, archive).
- Checking archived changes for the new rules.

## Impact

- Specs: `step-guidance` (new), `authored-formats` (modified)
- User-visible:
  - `wm instructions` shows a "Checklist" for the drafting steps and the "Shared rules" for every step, and its JSON gains `checklist` and `shared_rules`;
  - `wm check` reports a task item without `- Criteria:` or `- Verify:`, and a decision with fewer than two options;
  - the skills' Rules sections are shorter and point at the shared rules.
- Code: `services/instructions.py`, `views/` (the instructions view and its JSON schema), `record/` (tasks, design, changes)
- Assets and docs: all nine skills; concepts, `docs/json.md` (generated), the changelog.

## Outcome

- Built: wm instructions gives the propose, specs, design and tasks steps a checklist that marks the checks wm check enforces, and every step the five shared rules, in JSON as checklist and shared_rules; the nine skills point at the shared rules instead of repeating them; wm check reports an active item without a Criteria or Verify line (item-incomplete) and a decision with fewer than two options (decision-options).
- Differs: Don't merge stays in wm-pr and wm-fix because it is stricter than the shared rule. The Item has no criteria refusal in services/context.py is left in place though it can no longer be reached.

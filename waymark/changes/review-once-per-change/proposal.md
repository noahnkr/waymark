# Review once per change

Owner: Noah Roberts
Review: independent

## Why

Every task item gets its own review today: a self-review, or a fresh reviewer agent with `review: independent`. That makes a review step per item. Each independent review is a cold start of about 50k tokens, and each one checks a slice of the change rather than the whole.

Across the 8 independent reviews so far, none has found a bug. A slice is the wrong unit, because what goes wrong in a change usually sits between items: a criterion one item leaves to another, or a scenario no item covers. OpenSpec reviews once per change, against the requirements and their scenarios, with findings by severity. This is the second change on the `lighter-workflow` milestone. The first, `let-planner-build`, moved building into the session.

## What changes

- **The review level belongs to the change.** A `Review: self|independent|none` line in the proposal sets it, and the project's `default_review` applies when the line is absent. The short path still allows only `self` or `none`. `wm check` warns when a change modifies or removes a requirement and its level isn't `independent`.
- **One review per change, once every item is ticked.** It checks the whole change against its deltas' scenarios, the design and each item's criteria: is it complete, correct and coherent?
  - At `self`, the planner records it with `wm review <change> --self "<summary>"`.
  - At `independent`, the reviewer agent is started with the change's name alone and ends with `CHANGE: <change>` then `VERDICT: …`.
- **The review is recorded in a `## Review` section at the end of the task list.** It holds the same `(review)` and `(self-review)` lines as today. Findings go under a record as sub-lines, each with a severity (`critical`, `warning` or `suggestion`), a place and a text. A `pass` with a critical finding is refused.
- **A `changes` verdict names the items to rebuild.** `wm` reopens those items. Once they are ticked again, the change is reviewed again, independently. A second `changes` verdict, or a `spec-gap`, goes to the human as today, and `wm resolve <change> "<what was decided>"` frees the change.
- **The archive gate checks the change's review, not each item's.** A missing review can still be overridden by the human, with a reason that is recorded.
- **Per-item review goes away.** The `review:` tag on an item is an error in an active change, and `wm review`, `wm verdict` and the reviewer agent no longer take an item. Archived changes keep their old lines and are still shown as they were.
- **Skills, agent definitions, docs and the charter** are reworded to match. The pull request description lists the change's review instead of a review per item.

## Non-goals

- Archiving before the merge, and the tiny path. They are later changes on the milestone.
- Migrating changes in flight. There are none, and Waymark has no other project yet, so the old tag simply becomes an error.
- Grading findings automatically, or blocking on warnings and suggestions. They are advice.

## Impact

- New spec `review`: the change's review level, one review per change, the record and its findings, reopening named items, escalation to the human, the archive gate and the obsolete item tag.
- Spec `agent-results`: the reviewer ends with `CHANGE: <change>` instead of `ITEM: <change> <item>`; its purpose and the requirements that name the ending lines are modified.
- **Behavior change for every user, for the changelog:**
  - the record format changes: a `Review:` line in the proposal, a `## Review` section in the task list, and no `review:` tag on items;
  - `wm review`, `wm verdict` and `wm resolve` take a change where they took an item for reviews;
  - the reviewer agent is started with `<change>`;
  - `wm show --json` and `wm pr` show the review per change.
- Code: `record/` (proposal, tasks, state, fingerprint), `services/` (lifecycle, instructions, context, check, pr), `hooks/decide.py` (delegation and the reviewer's ending), `views/` and `cli.py`.
- Assets: `wm-apply`, `wm-propose`, `wm-update`, `wm-onboard` and `wm-pr`, and the `wm-reviewer` definition.
- Docs: concepts, getting started, the smoke test, architecture, the README and the regenerated CLI and JSON references.

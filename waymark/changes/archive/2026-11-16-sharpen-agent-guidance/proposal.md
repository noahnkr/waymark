# Sharpen agent guidance

- **Owner:** Noah Roberts

## Why

The reviewer grades findings from three one-line definitions, so the same problem can be a warning in one review and critical in the next, and a self-review grades by its own sense. The implementer is told not to guess, but not when to stop: it can keep retrying a failing check, or widen its item to fix something it noticed. Both agents' guidance lives only in their agent files, so a tool without those files, or the planner reviewing its own work, doesn't get it.

This is the last change on the `record-format-and-skills` milestone, split from `sharpen-drafting-skills`.

## What changes

- **Severity rubric:** `wm context --for review` and `wm instructions` at the review step give one rubric: a finding is critical when a criterion or scenario doesn't hold, the code does what a requirement forbids, or a check fails; a warning when everything holds but an edge is untested, a requirement is met by accident, or a likely next change breaks it; a suggestion for clarity, naming or duplication that no user would notice. When torn between two, pick the higher; every critical names the item to rebuild.
- **Stopping rules:** `wm context --for implement` gives the implementer the rules for when to stop and which result to end with: a spec gap, something outside the item, three failed attempts at the same check, and work the item doesn't ask for.
- **Agent definitions:** `wm-reviewer` and `wm-implementer` point at the pack for the rubric and the stopping rules instead of carrying their own versions. `wm-apply`'s self-review points at the rubric.

## Non-goals

- New review verdicts or severities.
- Enforcing the rubric: `wm` already refuses a pass with a critical finding, and judging severity stays with the reviewer.
- Changing how an agent's ending is recorded.

## Impact

- **Specs:** `agent-guidance` (new)
- **User-visible:**
  - `wm context --for review` and `wm instructions` at the review step show the severity rubric; `wm context --for implement` shows the stopping rules; their JSON gains `severity_rubric` and `stopping_rules`;
  - the `wm-reviewer`, `wm-implementer` and `wm-apply` texts point at them.
- **Code:** `services/context.py`, `services/instructions.py`, `views/` (the context pack and instructions views and their JSON schemas)
- Assets and docs: the two agent definitions and `wm-apply`; concepts and the changelog.

## Outcome

- **Built:** One severity rubric (critical, warning, suggestion, graded by what a finding breaks) given by the review context pack and by wm instructions at the review step; stopping rules (spec-gap, blocked, partial after three attempts, other work left to a note) given by the implement context pack; the reviewer, the implementer and wm-apply's self-review use them.
- **Differs:** none

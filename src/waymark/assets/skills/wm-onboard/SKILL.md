---
name: wm-onboard
description: Guide the human through their first Waymark change on their own code, explaining each step as it happens. Use after kickoff, or when someone is new to Waymark.
---

# Onboard

You are the planner, and this once also a guide. You run one real, small change through the whole workflow on the human's own code, and before each step you say in a sentence or two what the step is for. There is no demo project: the change is real and it stays.

## Steps

1. Run `wm status`. If the charter is still a skeleton, run the `wm-kickoff` skill first.
2. **Pick the change.** Ask the human for something small and real they want anyway: a fix, a doc correction, a small behavior. It should fit in one or two task items. Explain: everything in Waymark is a change, even the first one.
3. **Propose.** Explain: a proposal says why and what, before anything is built. Follow the `wm-propose` skill, on the short path if the change allows it.
4. **Specs.** If the change affects what the system does, explain: specs say what the system does; a delta is this change's edit to them. On existing code, the spec grows only where the change touches it.
5. **Tasks.** Explain: each item carries criteria and a way to verify it, so an agent can build it from the record alone.
6. **Accept.** Explain: this is the first of two approvals. Nothing is built before it, and only the human gives it. Ask them to run `wm accept <name>`.
7. **Apply and review.** Explain: a fresh implementer builds each item from the record; the review is recorded under the item. Follow the `wm-apply` skill.
8. **Look around.** Show `wm status`, `wm show <name>` and `wm inbox`. Explain: these come from the files alone, so any session can pick up from here.
9. **Archive.** Explain: this is the second approval. The deltas merge into the specs and the change moves to the dated archive. Follow the `wm-archive` skill.
10. **Wrap up.** Show `wm ls specs` and the archived change. Name what the human will use from now on: `wm-explore` for fuzzy ideas, `wm-propose` to start a change, `wm-apply` to build it, `wm-archive` to finish it, and `wm status` to see where things stand.

## Rules

- Keep each explanation to a sentence or two, given just before the step it explains.
- Every rule of the skills you follow applies here too. In particular, never run `wm accept`.
- If the human wants to stop partway, stop. `wm status` will show where to resume.

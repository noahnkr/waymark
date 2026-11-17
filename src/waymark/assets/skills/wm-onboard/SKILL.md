---
name: wm-onboard
description: Guide the human through their first Waymark change on their own code, explaining each step as it happens. Use after kickoff, or when someone is new to Waymark.
---

# Onboard

## Role

You are the planner, and this once also a guide. You run one real, small change through the whole workflow on the human's own code, and before each step you say in a sentence or two what the step is for. There is no demo project: the change is real and it stays.

## Inputs

- `wm status`. If the charter is still a skeleton, run the `wm-kickoff` skill first.
- Something small and real the human wants anyway.

## Steps

1. **Pick the change.** Ask the human for something small and real they want anyway: a fix, a doc correction, a small behavior. It should fit in one or two task items. Explain: everything in Waymark is a change, even the first one.
2. **Propose.** Explain: a proposal says why and what, before anything is built. Work takes one of three paths: tiny (no requirement changes, so no change at all), short (no design) or full, and `wm-propose` chooses it from what it finds. This first change should change a requirement, so it isn't tiny. Follow the `wm-propose` skill, on the short path if the change allows it.
3. **Specs.** If the change affects what the system does, explain: specs say what the system does; a delta is this change's edit to them. On existing code, the spec grows only where the change touches it.
4. **Tasks.** Explain: each item carries criteria and a way to verify it, so it can be built from the record alone. By default the planner builds each item in this session; an item with a `- Build: delegate` line goes to a fresh implementer instead.
5. **Accept.** Explain: this is the first of two approvals. Nothing is built before it, and only the human gives it. Ask them to run `wm accept <name>`.
6. **Apply and review.** Explain: the planner builds each item from the record, writing down first anything the record lacks, and hands a tagged item to a fresh implementer. Once every item is built, the whole change is reviewed once, at the level its proposal sets, and the review and its findings are recorded at the end of the task list. Follow the `wm-apply` skill.
7. **Look around.** Show `wm status`, `wm show <name>` and `wm inbox`. Explain: these come from the files alone, so any session can pick up from here.
8. **Archive.** Explain: this is the second approval. The deltas merge into the specs and the change moves to the dated archive. Follow the `wm-archive` skill.
9. **Wrap up.** Show `wm ls specs` and the archived change. Name what the human will use from now on: `wm-explore` for fuzzy ideas, `wm-propose` for any work, from a tiny fix to a change, `wm-apply` to build it, `wm-archive` to finish it, and `wm status` to see where things stand.

## Quality bar

- The change is real, small, and one the human wanted anyway.
- Each explanation is a sentence or two, given just before the step it explains.
- Every step follows the skill it names, with that skill's rules.

## Show the human

Before each step, one or two sentences on what the step is for. Then what that step's skill shows. At the wrap-up, the list of skills and commands they'll use from now on.

## When to stop

- The human wants to stop partway: stop. `wm status` will show where to resume.
- The change turns out to be tiny: follow `wm-propose`'s tiny path instead, and say why the first change usually isn't tiny.
- The change is archived and the wrap-up is shown.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Keep each explanation to a sentence or two, given just before the step it explains.
- Every rule of the skills you follow applies here too.

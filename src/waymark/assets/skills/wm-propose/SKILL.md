---
name: wm-propose
description: Draft a Waymark change for the human to accept - the proposal, the spec deltas, the design and the task list. Use when the human wants to build or change something.
---

# Propose

You are the planner. You draft every artifact of a change; the human reads them and decides. Nothing is built until they accept the change.

## Steps

1. Agree on a name with the human: kebab-case, starting with a verb, such as `add-search-limit`. Ask whether this is a small change. A small change takes the short path: no design, and a review level of `self` or `none`. Then run `wm new change <name>`, with `--short` for the short path.
2. Repeat until the next step is `accept`:
   - Run `wm instructions --change <name> --json`. It names the step, the file to write, its template, the project's rules for this step, and what to read first.
   - Read what it lists. Draft the file from the template. Keep the headings and formats exactly; they are parsed.
   - Run `wm check`. Fix every error in the files you wrote before moving on.
   - Show the human what you drafted and take their corrections.
3. The steps come in this order:
   - **propose**: why, what changes, non-goals, impact. Under Impact, name the specs the change touches or write "No spec changes".
   - **specs**: one delta file per spec. Agree on what the system does before deciding how.
   - **design**: how it will be built, with each decision's options, choice and reason. Skipped on the short path.
   - **tasks**: items small enough to build from the record alone. Every item needs criteria that can be checked and a way to verify it.
4. Suggest the change's review level. The change is reviewed once, as a whole, after every item is built. Add a `Review: independent` line under the Owner line when it modifies or removes an existing requirement, or touches security, data integrity or money; `Review: none` for docs, renames and changes of a few lines. Leave the line out for the project default. Items carry no review level.
5. Suggest who builds each item. By default the planner builds it in the session. Tag an item `build: delegate` to have a fresh implementer build it from the record alone: for a large item, for items that can be built in parallel, or where a cold check that the record is enough to build from is worth its cost. The tag goes at the end of the item line. Leave other items untagged.
6. When `wm instructions` says the next step is `accept`, summarize the change for the human: what it does, the deltas, the decisions, the review level and the build tags you suggested. Ask them to run `wm accept <name>` themselves.

## Rules

- Only the human accepts a change. Never run `wm accept`.
- Don't tick items, and don't write `Accepted:`, `Blocked:`, `Spec gap:` or review lines. `wm` writes those.
- Don't edit files under `waymark/specs/`. Write deltas in the change instead.
- If the record doesn't say enough to draft something, ask the human. Don't guess.
- Write no code in this skill.

---
name: wm-propose
description: Draft a Waymark change for the human to accept - the proposal, the spec deltas, the design and the task list. Use when the human wants to build or change something.
---

# Propose

You are the planner. You draft every artifact of a change; the human reads them and decides. Nothing is built until they accept the change.

## Steps

1. Agree with the human on the path the work takes:
   - **tiny:** it adds, changes or removes no requirement, such as a typo, a docs fix, a bug where the code disagrees with a spec, or a refactor. It needs no change: hand over to the `wm-fix` skill and stop here;
   - **short:** a small change with no design, and a review level of `self` or `none`;
   - **full:** a change with a design.

   Then agree on a name: kebab-case, starting with a verb, such as `add-search-limit`. Run `wm new change <name>`, with `--short` for the short path.
2. Repeat until the next step is `accept`:
   - Run `wm instructions --change <name> --json`. It names the step, the file to write, its template, the project's rules for this step, and what to read first.
   - Read what it lists. Draft the file from the template. Keep the headings and formats exactly; they are parsed.
   - Run `wm check`. Fix every error in the files you wrote before moving on.
   - Show the human what you drafted and take their corrections.
3. The steps come in this order:
   - **propose**: why, what changes, non-goals, impact. The Impact has three lines, each with text or nested bullets: `- Specs:` naming each spec the change has a delta for, in backticks, or `- Specs: none`; `- User-visible:` with what users will see change, for the changelog; and `- Code:` with the parts of the code it touches. `wm check` compares `Specs:` with the deltas.
   - **specs**: one delta file per spec, with `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements` sections as needed; a rename is a `- From: <old name>` line and a `- To: <new name>` line, and keeps the requirement's text. Agree on what the system does before deciding how. Requirements describe what the system does, as a user or another program sees it; files the user doesn't touch, internals and mechanisms go in the design.
   - **design**: how it will be built, with each decision's options, choice and reason. Skipped on the short path. Each decision has a `- Status:` line, `proposed` until the human has settled it and then `decided`, and a `- Decided by:` line, `human` when the human made the call and `planner` when you did. List what is still undecided under `## Open questions`, or write `None.`. The change can't be accepted while a decision is proposed or a question is listed: bring each one to the human, then record their answer.
   - **tasks**: items small enough to build from the record alone. Every item needs criteria that can be checked and a way to verify it. When an item has several criteria, write them as a nested list under `- Criteria:`, one per bullet; likewise, several ways to verify it go as a nested list under `- Verify:`, one step per bullet.
4. Suggest the change's review level. The change is reviewed once, as a whole, after every item is built. Add a `- Review: independent` line under the `- Owner:` line when it modifies or removes an existing requirement, or touches security, data integrity or money; `- Review: none` for docs, renames and changes of a few lines. Leave the line out for the project default. Items carry no review level.
5. Suggest who builds each item. By default the planner builds it in the session. Add a `- Build: delegate` line under an item to have a fresh implementer build it from the record alone: for a large item, for items that can be built in parallel, or where a cold check that the record is enough to build from is worth its cost. Leave other items without it.
6. When `wm instructions` says the next step is `accept`, summarize the change for the human: what it does, the deltas, the decisions and who made each, the review level and the items you suggested to delegate. Ask them to run `wm accept <name>` themselves.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Work through the step's checklist from `wm instructions` before moving on: `wm check` holds the checks marked `wm`, and you judge the rest.
- Write deltas in the change, never in `waymark/specs/`.
- Write no code in this skill.

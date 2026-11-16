---
name: wm-propose
description: Draft a Waymark change for the human to accept - the proposal, the spec deltas, the design and the task list. Use when the human wants to build or change something.
---

# Propose

## Role

You are the planner. You draft every artifact of a change; the human reads them and decides. Nothing is built until they accept the change.

## Inputs

- What the human wants built or changed, in their words.
- `wm status` and `wm context --for explore`: the charter, the specs, and what is already in flight.
- For each step, `wm instructions --change <name> --json`: the file to write, its template, the step's guidance and checklist, the project's rules for the step, and what to read first.

## Steps

1. **Path and name.** Agree with the human on the path the work takes:
   - **tiny:** it adds, changes or removes no requirement, such as a typo, a docs fix, a bug where the code disagrees with a spec, or a refactor. It needs no change: hand over to the `wm-fix` skill and stop here;
   - **short:** a small change with no design, and a review level of `self` or `none`;
   - **full:** a change with a design.

   Then agree on a name: kebab-case, starting with a verb, such as `add-search-limit`. Run `wm new change <name>`, with `--short` for the short path.
2. **Questions.** Before drafting, list what the record doesn't settle for this change: its scope, how it behaves at the edges, names, and what is left out. Ask the human, a few questions at a time, each with the answer you recommend. Write their answers into the artifacts as you draft them; an answer that stays in the conversation is lost to the next session.
3. **Draft, step by step,** until the next step is `accept`:
   - Run `wm instructions --change <name> --json` and read what it lists. Draft the file from the template. Keep the headings and formats exactly; they are parsed.
   - Follow the step's guidance, including its writing rules (specs) and sizing rules (tasks), and work through its checklist: `wm check` holds the checks marked `wm`, and you judge the rest.
   - Run `wm check`. Fix every error in the files you wrote before moving on.
   - Show the human what you drafted and take their corrections.
4. **The drafting steps,** in order:
   - **propose**: why, what changes, non-goals, impact. The Impact has three lines, each with text or nested bullets: `- Specs:` naming each spec the change has a delta for, in backticks, or `- Specs: none`; `- User-visible:` with what users will see change, for the changelog; and `- Code:` with the parts of the code it touches.
   - **specs**: one delta file per spec, with `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements` sections as needed; a rename is a `- From: <old name>` line and a `- To: <new name>` line, and keeps the requirement's text. Agree on what the system does before deciding how.
   - **design**: how it will be built, with each decision's options, choice and reason. Skipped on the short path. Each decision has a `- Status:` line, `proposed` until the human has settled it and then `decided`, and a `- Decided by:` line, `human` when the human made the call and `planner` when you did. List what is still undecided under `## Open questions`, or write `None.`. The change can't be accepted while a decision is proposed or a question is listed: bring each one to the human, then record their answer.
   - **tasks**: items small enough to build from the record alone, each with criteria that can be checked and a way to verify it. Several criteria go as a nested list under `- Criteria:`, one per bullet; several ways to verify go under `- Verify:` the same way.
5. **Review level.** Suggest one. The change is reviewed once, as a whole, after every item is built. Add a `- Review: independent` line under the `- Owner:` line when it modifies or removes an existing requirement, or touches security, data integrity or money; `- Review: none` for docs, renames and changes of a few lines. Leave the line out for the project default. Items carry no review level.
6. **Who builds.** By default the planner builds each item in the session. Add a `- Build: delegate` line under an item to have a fresh implementer build it from the record alone: for a large item, for items that can be built in parallel, or where a cold check that the record is enough to build from is worth its cost. Leave other items without it.
7. **Consistency check.** When `wm instructions` says the next step is `accept`, check the artifacts against each other before showing the summary:
   - the Impact's `Specs:` names exactly the deltas (`wm check` holds this);
   - every scenario in the deltas is covered by some item's criteria;
   - the design's approach covers every requirement in the deltas and adds none of its own;
   - the tasks touch what the Impact's `Code:` line names, and nothing it doesn't;
   - each decision's choice is what the approach does.

   Fix what doesn't agree, with the human where it changes what they agreed to.
8. **Accept.** Show the acceptance summary and ask the human to run `wm accept <name>` themselves.

## Quality bar

- Every answer the human gave is written in an artifact, not only said in the conversation.
- The deltas say what the system does, as a user sees it; the design says how; neither repeats the other.
- Every scenario is covered by an item, and every item can be built from the record alone.
- Every decision says who made it, and none is left proposed.
- `wm check` is healthy, and the step's checklist holds.

## Show the human

After each step, what you drafted, in a few lines. Before acceptance, this summary:

- **What it does:** two or three sentences.
- **Deltas:** per spec, the requirements added, modified, removed or renamed.
- **Decisions:** each one, with who made it.
- **Review level:** and why.
- **Items:** each with a line on what it builds, and which you suggest to delegate.

Then ask for `wm accept <name>`.

## When to stop

- The work is tiny: hand over to `wm-fix`.
- The human's answer to a question changes the scope: stop, and agree the new scope before drafting on.
- The record can't say what the human wants without a decision only they can make: ask, and wait.
- The next step is `accept`: show the summary and stop. Only the human accepts.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Write deltas in the change, never in `waymark/specs/`.
- Write no code in this skill.

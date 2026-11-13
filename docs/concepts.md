# Concepts and glossary

Waymark rests on one idea: **agents only know what is written down.** Everything
an agent needs to do its job is in the record, in plain markdown in your
repository, and everything it does is written back there. That is what lets you
stop any session anywhere, and lets the next one, or the next person, pick up from
the files alone.

## The workflow

Every piece of work is a **change**, including a project's first build and the
first work on an existing codebase. A change goes through these steps:

```
explore    optional: think an idea through; nothing is written unless you ask
propose    the proposal: why, what changes, non-goals, impact
specs      deltas: the change's edits to the living specs
design     how it will be built, and the decisions taken (skipped on the short path)
tasks      one checklist; each item has criteria, a way to verify it, a review level
accept     YOU approve the change; nothing is built before this
apply      each item built by a fresh implementer agent, from the record alone
review     each item checked at its level, and the check written under it
archive    YOU approve finishing it; deltas merge into the specs, the outcome is written
```

Agents draft every artifact; you approve at the two gates, **accept** and
**archive**. Specs come before design: first agree on what the system does, then
on how.

**Changing an accepted change withdraws its acceptance.** That covers the
proposal, the deltas, the design and each task item's definition (its number,
title, criteria, verification, repo and review level). It needs accepting again.
Ticks, blockers, review records and notes don't count.

**Several changes can be in flight at once.** Two changes that name the same
requirement *overlap*: `wm check` reports it and neither is blocked. Whichever
is archived first wins; the other is then revised against the new spec and
accepted again before it can be archived.

**A decision is reversed by a new change.** The specs are always the sum of the
archived changes, and the archive keeps the history of why.

## The files

```
waymark/
  config.toml          settings: the pinned wm version, the default review level, ...
  charter.md           vision, goals, non-goals, constraints, glossary, context, rules
  specs/<area>.md      one living spec per area of the system
  changes/<change>/    proposal.md, specs/<area>.md (deltas), design.md, tasks.md
  changes/archive/     archived changes, each in a dated folder
  milestones/          optional: a goal and a roadmap of changes
  explorations/        saved thinking
```

There is no stored status and no frontmatter. Facts are plain lines, such as
`Owner:` and `Accepted:` in a proposal, and everything else is worked out from
where files are and what they say. Templates are built into `wm`;
`wm instructions` hands an agent the right one at each step.

A spec states what one area of the system does, as requirements, each with at
least one scenario:

```markdown
### Requirement: Result limit
A search SHALL return at most fifty results.

#### Scenario: Many matches
- GIVEN an index where a query matches more than fifty documents
- WHEN the search runs
- THEN fifty results come back
```

A task item carries what an agent needs to build it, and what `wm` writes about it:

```markdown
- [x] 1.1 Cap the result count   `review: independent`
  - Criteria: at most fifty results come back
  - Verify: a test searches an index with fifty-one matches
  - (review) 2026-01-15 pass: the boundary is covered
```

## Who does what

| | Planner | Implementer | Reviewer |
|---|---|---|---|
| Is | the main agent session, working with you | a fresh agent, started with `<change> <item>` and nothing else | a fresh agent, started the same way |
| Sees | the charter, `wm status`, whatever you bring in | its item, the proposal, deltas, design, the requirements they touch, the project's context and apply rules | its item, the deltas and their scenarios, the code; **not** how it was built |
| May | explore, draft and edit artifacts, delegate, record self-reviews, archive | edit code (in an atlas, only in its item's repo) and add notes under its item | read code and the record; run tests and other read-only commands |
| Ends with | | `ITEM: <change> <item>` then `RESULT: done / partial / spec-gap / blocked` | `ITEM: <change> <item>` then `VERDICT: pass / changes / spec-gap` |

Only you accept a change. Code is always built by an implementer, so it is
always built from the record alone.

## Review levels

| Level | For | What is recorded |
|---|---|---|
| `self` (the default) | ordinary work | the planner checks the item against its criteria and scenarios, and records a `(self-review)` line |
| `independent` | risky work: an item that modifies or removes an existing requirement, touches security, data integrity or money, or is being redone after a failed review | a reviewer agent's verdict, written by `wm` from the reviewer's own words |
| `none` | docs, renames, changes of a few lines | nothing |

The planner suggests levels when it drafts the tasks; accepting the change
confirms them. A `changes` verdict sends the item back to be rebuilt, and from
then on it needs an independent pass. A second `changes` verdict, or a
`spec-gap`, goes to you.

## The gates

| Gate | Stops | Who can pass it |
|---|---|---|
| **Accept** | applying any item of a change that isn't accepted, or whose acceptance was withdrawn | only you, with `wm accept` |
| **Delegation** | starting an implementer or reviewer unless the prompt names exactly one item, the item has criteria, and the record around it is sound | no one; fix the record |
| **Archive** | archiving a change that isn't accepted, has unbuilt or unreviewed items, or a delta that no longer applies | only a missing review can be overridden, by you, with a reason that is recorded |

**Evidence is written only by `wm`**: acceptance, ticks, blockers, spec gaps and
review records. Agents report their results in their last lines, and `wm`'s
hooks write the evidence from them. Agents that try to write evidence by hand are
refused, and `wm check` flags evidence that doesn't follow the format. These are
guard rails against mistakes and shortcuts, not security against someone set on
getting around them. In Claude Code the agent-side rules are enforced by its
hooks; in a tool without hooks they rely on the agents following the skills.

## Glossary

| Term | Meaning |
|---|---|
| **Record** | Everything Waymark keeps in plain markdown: the charter, specs, changes, milestones and explorations. The single source of truth agents work from. |
| **Charter** | What the project is: vision, goals, non-goals, constraints and glossary, plus the facts every agent must know (Context) and project rules for each workflow step (Rules). |
| **Spec** | The living description of what one area of the system does. It changes only when a change is archived or synced. |
| **Requirement** | One statement in a spec of what the system SHALL do, with at least one scenario. Its heading is its key. |
| **Scenario** | A GIVEN / WHEN / THEN example of a requirement. Reviews check work against scenarios. |
| **Atlas** | A separate repository that holds the record for a project whose code spans several repositories. See the [multi-repo guide](multi-repo.md). |
| **Change** | One unit of work, from idea to archive, in its own folder: proposal, deltas, design and tasks. |
| **Proposal** | Why a change is wanted, what it changes, its non-goals and impact. Its outcome is added at archive. |
| **Delta** | A change's edits to one spec: requirements added, modified or removed. Deltas merge into the specs at archive. |
| **Design** | How a change will be built, including its decisions: the options, the choice and why. |
| **Task item** | One checkbox in a change's task list, with its criteria, how to verify it, its review level and the record of building and reviewing it. |
| **Acceptance** | Your explicit approval of a change before any of it is built. Only you can give it. |
| **Short path** | The light route for a small change: no design, and review level `self` or `none`. Marked by a `Path: short` line in the proposal. |
| **Conflict** | A delta that no longer applies to its spec (a *mismatch*, which blocks its change), or two active changes that name the same requirement (an *overlap*, which is reported). |
| **Sync** | Merging an applied change's deltas into the specs without archiving it yet. |
| **Archive** | Finishing a change: its deltas merged into the specs, its outcome written, and its folder moved to a dated archive. |
| **Owner** | The one person responsible for a change. |
| **Exploration** | Saved thinking on a topic (questions, approaches, a conclusion) that may lead to a change or be parked. |
| **Milestone** | An optional goal that several changes work toward, with a roadmap listing them. |
| **Planner** | The main agent session, working with you: it explores, drafts, delegates and archives. |
| **Implementer** | A fresh agent that builds one task item from the record alone. |
| **Reviewer** | A fresh, read-only agent that checks one task item against its criteria and scenarios, without seeing how it was built. |
| **Review level** | How a task item is checked: `self`, `independent` or `none`. |
| **Context pack** | The excerpts of the record that `wm` assembles for one job: exploring, implementing or reviewing. |
| **Spec gap** | What an agent reports when the record isn't enough to do its job, instead of guessing. It goes to you. |

# Concepts and glossary

Waymark rests on one idea: **agents only know what is written down.** Everything
an agent needs to do its job is in the record, in plain markdown in your
repository, and everything it does is written back there. That is what lets you
stop any session anywhere, and lets the next one, or the next person, pick up from
the files alone.

## The workflow

Work that changes what the system does is a **change**, including a project's
first build and the first work on an existing codebase. Work that changes no
requirement takes the [tiny path](#paths) and needs no change. A change goes
through these steps:

```
explore    optional: think an idea through; nothing is written unless you ask
propose    the proposal: why, what changes, non-goals, impact
specs      deltas: the change's edits to the living specs
design     how it will be built, and the decisions taken (skipped on the short path)
tasks      one checklist; each item has criteria and a way to verify it
accept     YOU approve the change; nothing is built before this
apply      each item built from the record: by the planner, or by a fresh
           implementer agent when its `- **Build:**` line says `delegate`
review     the whole change checked once, at its level, and the review written
           in the Log at the end of the task list
archive    YOU approve finishing it, on the change's branch before its pull request;
           deltas merge into the specs, the outcome is written
```

Agents draft every artifact; you approve at the two gates, **accept** and
**archive**. The archive goes on the change's branch before its pull request, so the
code, the merged specs and the archived change are reviewed and merged together.
If the pull request needs more work, the archive commit is reverted and the
change archived again. Specs come before design: first agree on what the system does, then
on how.

## Branches

Each change lives on a branch named after it, and merges on its own.

- **Base:** a change branches from the default branch, the `origin` remote's HEAD
  or `main`. A change that needs another change not merged yet says so with an
  `- **After:** <change>` line, written by `wm new change <name> --after <change>`,
  and branches from that change's branch instead.
- **Shown:** `wm instructions` and `wm pr` give a change's branch and base, and
  its pull request goes into the base. `wm status` adds an `on <base>` line under
  a change whose base isn't the default branch.
- **Merged base:** once the change it comes after is archived or merged, `wm
  check` warns: rebase onto the default branch, retarget the pull request, and
  take the `- **After:**` line off.
- **Milestones:** a new milestone goes on a `plan-<milestone>` branch and lands
  on the default branch in a plan pull request before its changes are proposed.

`wm` names branches; it never creates, switches, rebases or pushes them. The
skills do that with git. In an atlas, a change uses the same branch name in every
repo.

## Paths

| Path | For | What it takes |
|---|---|---|
| **Tiny** | work that adds, changes or removes no requirement: a typo, a docs fix, a bug where the code disagrees with a spec, a refactor, a dependency bump | no change folder: `/wm-propose` says in one line what it will change and the requirement it keeps to, builds after your yes, then commits and offers a pull request. Nothing is written to the record; your merge is the second approval |
| **Short** | a small change | a change with a proposal, deltas and a task list, but no design (a `- **Path:** short` line); review level `self` or `none` |
| **Full** | anything bigger | a change with a design, and an independent review when it is risky |

The test for tiny is the specs, not the size: if every requirement still holds
as written, the work is tiny. `/wm-propose` finds out which it is by reading
the specs and the code. A change with a question still open takes the full
path, where the design's open questions hold it until you answer. If tiny work
turns out to change a requirement, it stops and becomes a change. Specs can't
be edited by hand on any path.

**Changing what was accepted withdraws the acceptance.** That covers the
proposal (its `- **Review:**` line included), the deltas, the design and the
definition of each item the acceptance names (its number, title, criteria,
verification, repo and `- **Build:**` line), including removing the item. It needs
accepting again. Ticks and records, such as blockers, notes and reviews,
don't count. Neither does layout: the fingerprint is taken over the standard
layout, so `wm check --fix` never withdraws an acceptance.

**Adding an item keeps the acceptance.** The acceptance is a record in the task
list's Log that names the items it covers, and an item added later is built like
any other:

```
- 2026-01-15 (accepted) fingerprint 6cec39a287bf99f2 items 1.1, 1.2 by Sam Doe
```

Accepting again adds a new `(accepted)` record; the latest one counts.

**Several changes can be in flight at once.** Two changes that name the same
requirement *overlap*: `wm check` reports it and neither is blocked. Whichever
is archived first wins; the other is then revised against the new spec and
accepted again before it can be archived.

**A decision is reversed by a new change.** The specs are always the sum of the
archived changes, and the archive keeps the history of why.

## Explorations

An exploration is saved thinking on an idea that isn't a change yet: research,
or an idea kept for later. `/wm-explore` saves one when you pick that offer. Its
`- **Status:**` line says where it stands, and only `wm` writes it.

| Status | Means | Written by |
|---|---|---|
| `open` | waiting to be decided or built | `wm new exploration <name>` |
| `led-to <links>` | its findings went into a change or milestone | `wm new change <name> --from <exploration>` or `wm new milestone <name> --from <exploration>` |
| `dropped` | weighed, and won't be acted on | `wm exploration drop <exploration> --reason "<why>"` |

- **Picking one back up:** `/wm-explore <exploration>` reads it, says what in
  the record has changed since, and goes on from its Questions and Approaches.
  It ends with four offers: do nothing, update it or drop it, start a proposal,
  or start a milestone.
- **Ending:** an exploration that led to work moves to `explorations/archive/`
  when `wm archive` or `wm close` finishes everything it led to. A dropped one
  moves there at once. Links to it are re-aimed, so nothing is left to tidy.

[The record](record.md#exploration) covers its sections and checks.

## Resources

Some of what an agent needs can't be found in the code: the CRM your app reads
its leads from, how it's set up for each environment, and where the settings to
reach its API live. A **resource** holds those facts for one service, platform,
account, database, dataset or document, in `resources/<name>.md`.

- **Specs and resources:** a spec says what your system does, and changes only
  through a change. A resource says what something outside the repo is, and is
  edited by hand whenever that thing changes, inside a change or as tiny work.
- **Serves:** its `- **Serves:**` line names the specs it supports, such as
  `leads` for the CRM.
- **For agents:** the explore pack lists every resource. The implement and
  review packs carry each active resource that serves a spec the change has a
  delta for.
- **No secrets:** a resource says where a secret lives, never the secret.

`wm new resource <name> <kind>` creates one. [The record](record.md#resource)
covers its sections and checks.

## The files

```
waymark/
  config.toml          settings: the pinned wm version, the default review level, ...
  charter.md           vision, goals, non-goals, constraints, glossary, context, rules
  specs/<area>.md      one living spec per area of the system
  changes/<change>/    proposal.md, specs/<area>.md (deltas), design.md, tasks.md
  changes/archive/     archived changes, each in a dated folder
  milestones/<name>/   optional: milestone.md, a goal and a roadmap of changes
  explorations/        saved thinking; explorations/archive/ once it ends
  resources/<name>.md  facts about one thing outside the repo: a service, a platform, ...
```

There is no stored status and no frontmatter. What you write uses
`- **<Label>:**` lines, such as `- **Owner:**` in a proposal or `- **Criteria:**` under an
item (see [What you write](#what-you-write)). What `wm` writes is a record (see
[Records](#records)). Everything else is worked out from where files are and
what they say. Templates are built into `wm`; `wm instructions` hands an agent
the right one at each step.

`wm instructions` also gives every step the rules all the skills share: only
you accept a change or archive one past a missing review, only `wm` writes
records, the specs change only by archiving or syncing, the record is never
filled in by guessing, and nothing is pushed, opened as a pull request or merged
without your yes. Each drafting step (propose, specs, design, tasks) also gets a
checklist of what must hold before moving on; a check marked `wm` is one that
`wm check` enforces, and the agent judges the rest. The specs step also gives
the rules for writing requirements, and the tasks step the rules for sizing
items.

Every skill `wm init` installs has the same sections: Role, Inputs, Steps, any
sections of its own, Quality bar, Show the human, When to stop and Rules. Show
the human gives the fixed shape of what the skill tells you, such as the summary
`wm-propose` shows before you accept, and When to stop says when it hands back
to you.

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

Each fact has one place to go:

| The fact | Where it goes |
|---|---|
| What the system does | A requirement in the area's spec. |
| A fact about one area that isn't a requirement, such as where its data comes from | The spec's `## Background`, set through a delta. |
| A fact about something outside the repo, such as a service or a platform | A resource, `resources/<name>.md`. |
| A fact every agent needs on every change | The charter's Context. |

A spec's Background reaches only the agents working on a change with a delta for
that spec. See [Spec](record.md#spec-specsareamd).

A task item carries what an agent needs to build it, and the records `wm`
writes about it. The records about the whole change sit in a `## Log` section at
the end of the task list:

```markdown
- [x] 1.1 Cap the result count
  - **Build:** planner
  - **Criteria:**
    - at most fifty results come back
    - they are the fifty best matches
  - **Verify:**
    - a test searches an index with fifty-one matches
    - `wm check` here

## Log

- 2026-01-15 (accepted) fingerprint 6cec39a287bf99f2 items 1.1 by Sam Doe
- 2026-01-15 (note) 1.1 by Sam Doe: the cap sits after sorting
- 2026-01-16 (review) pass covers 1.1 by wm-reviewer: the boundary is covered
  - [suggestion] `docs/search.md`: name the limit in the help text
```

### What you write

You and your agents write sections of prose and label lines, the label in bold
with the colon inside, `- **<Label>:**`: a proposal's
`- **Owner:**` and its Impact's `- **Specs:**`, `- **User-visible:**` and `- **Code:**`; an
item's `- **Build:**`, `- **Criteria:**` and `- **Verify:**`, in that order; a
decision's `- **Status:**`, `- **Decided by:**`, and its options as a nested list
under `- **Options:**`. `wm check` reports a label written plain, and
`wm check --fix` makes it bold. An exploration's `- **Status:**` is written by `wm`
(see [Explorations](#explorations)). Each note has a fixed set of sections, and
`wm check` holds it to them.
[The record](record.md) covers every note in detail: its sections, the lines it
can hold, who writes and updates it, and its checks.

The layout rules for the Impact, the decisions and the charter's numbered lists
hold for active work. Archived changes are read as they were written.

### Records

Every line `wm` writes is a dated record of one shape:

```
YYYY-MM-DD (<kind>) [<args>] [by <who>]: <text>
```

A list of items among the arguments is separated by `, `, and a list that
another argument follows ends with `;`.

Every record of a change goes in the `## Log` at the end of its task list, in
the order it was written. An item holds only its definition and its tick.

| About | Kinds | Example |
|---|---|---|
| One item, named after the kind | `(blocked)`, `(gap)`, `(note)`, `(reopened)`, `(resolved)` | `2026-11-20 (blocked) 1.2 by Ada: the API key is missing` |
| The whole change | `(accepted)`, `(synced)`, `(self-review)`, `(review)`, `(resolved)`, `(override)` | `2026-11-20 (resolved) by Ada: keep the cap` |

`wm show` and the implement context pack gather each item's records from the
Log and show them with the item. `wm check` reports a record written under an
item as `misplaced-record`.

- **Who:** your git name, `wm-implementer` or `wm-reviewer` for an agent's
  result, or the `--by` value that every writing command takes.
- **Never edited:** a later record supersedes an earlier one. `wm resolve` adds
  a `(resolved)` record and the blocker stays.
- **Notes:** `wm note <change> <item> "<text>"` writes one about an unticked
  item in the Log.
- **Covers:** a `(review)` or `(self-review)` record names the items it covers,
  as `covers <item>...` before `by`. A record without `covers`, written before
  Waymark had it, covers every item.
- **Layout:** `wm check --fix` puts the record in its standard layout: list
  markers, blank lines before headings, trailing spaces, the final line break
  and the records' own shape. It never changes wording, fenced code, comments
  or links, and never touches the archive.

## Who does what

| | Planner | Implementer | Reviewer |
|---|---|---|---|
| Is | the main agent session, working with you | a fresh agent, started for an item with a `- **Build:** delegate` line, with `<change> <item>` and nothing else | a fresh agent, started for a change at review level `independent` with `<change>` and nothing else |
| Sees | the charter, `wm status`, whatever you bring in | its item, the proposal, deltas, design, the requirements they touch and their specs' Background, the resources that serve those specs, the project's context and rules, its milestone's Goal and Non-goals, and when to stop | the criteria of the items to review, the deltas and their scenarios, their specs' Background and resources, the design, earlier reviews and what each covers, its milestone's Goal and Non-goals, the severity rubric, the code; **not** how it was built |
| May | explore, draft and edit artifacts, build items and make tiny fixes (in an atlas, in any code repo), delegate, record results and self-reviews, archive | edit code (in an atlas, only in its item's repo) and leave notes on its item with `wm note` | read code and the record; run tests and other read-only commands |
| Ends with | | `ITEM: <change> <item>` then `RESULT: done / partial / spec-gap / blocked` | `FINDING:` lines, then `CHANGE: <change>` then `VERDICT: pass / changes <items> / spec-gap` |

[Skills and agents](skills.md) covers each skill and agent in detail.

Only you accept a change. The record is the source of truth: whoever builds an
item builds it from the record. A fact the record lacks is written into it
first, or reported as a spec gap.

The implementer's context pack says when to stop and which result to end with:
a spec gap, something outside the item, or three failed attempts at the same
check. Every review, independent or a self-review, grades its findings by one
severity rubric: critical when a criterion or scenario doesn't hold, warning
when everything holds but something is fragile, suggestion for clarity. The
review context pack and `wm instructions` at the review step both give it.

## Who builds an item

Every item has a `- **Build:**` line, first among its lines. With
`- **Build:** planner`, the planner builds the item itself. It reads the item's context pack
(`wm context <change> <item> --for implement`), builds the item, runs the checks
the item touches, and records the result with `wm tick`, `wm block` or `wm gap`.

An item with `- **Build:** delegate` goes to a fresh implementer instead:

```markdown
- [ ] 1.2 Rebuild the search index
  - **Build:** delegate
  - **Criteria:** the index holds every document
  - **Verify:** a search finds a document added last
```

- **When to delegate:** a large item, items that can be built in parallel, or an
  item where a cold check that the record is enough to build from is worth its
  cost.
- **Where:** the first line under the item. The values are `planner` and
  `delegate`; `wm check` reports any other, and an item without the line.
- **Accepted with the item:** adding, removing or changing the line withdraws
  acceptance.
- **Guidance, not a gate:** the line decides what `wm instructions` and the
  skills say. The hooks don't enforce it.

## Review

A change is reviewed once, as a whole, after every item is ticked. The review
checks it against its deltas' scenarios, its design and each item's criteria: is
it complete, correct and coherent?

The change's level is the `- **Review:**` line in its proposal, or the project's
`default_review` when the line is absent:

| Level | For | What is recorded |
|---|---|---|
| `self` (the usual default) | ordinary work | the planner reviews the change and records a `(self-review)` line with `wm review <change> --self` |
| `independent` | risky work: a change that modifies or removes an existing requirement, or touches security, data integrity or money | a reviewer agent's verdict, written by `wm` from the reviewer's own words |
| `none` | docs, renames, changes of a few lines | nothing |

- **Findings:** each review can carry findings, given as
  `<critical | warning | suggestion>: <place>: <text>` and written under it as
  ``- [<severity>] `<place>`: <text>``. A place that holds `: ` is given in
  backticks. A `pass` or a self-review with a critical finding is refused.
- **Changes:** a `changes` verdict names the items to rebuild, such as
  `2026-01-15 (review) changes 1.2, 2.1; covers 1.1, 1.2, 2.1 by wm-reviewer: <reasons>`. Those
  items are reopened and built again, and the change then needs an independent review.
- **Added items:** an item added after a passing review is reviewed on its own.
  Once it is ticked, the next step is a review of the items no passing review
  covers, at the change's level. The reviewer's pack holds only those items, and
  the record covers just them, such as
  `2026-01-20 (review) pass covers 1.3 by wm-reviewer: <reasons>`. The items the
  earlier review passed aren't reviewed again.
- **To you:** a second `changes` verdict, or a `spec-gap`, goes to you. You
  record your decision with `wm resolve <change> review "<what was decided>"`.
- **Warning:** `wm check` warns when a change modifies or removes a requirement
  and its level isn't `independent`.
- **Short path:** the level is `self` or `none`.

## The gates

| Gate | Stops | Who can pass it |
|---|---|---|
| **Accept** | applying any item of a change that isn't accepted, or whose acceptance was withdrawn | only you, with `wm accept` |
| **Delegation** | starting an implementer unless the prompt names exactly one item that has criteria; starting a reviewer unless the prompt names one change whose items are all ticked and which needs an independent review it lacks; either while the record around it isn't sound | no one; fix the record |
| **Archive** | archiving a change that isn't accepted, has unbuilt items, isn't reviewed, has an item no passing review covers, or has a delta that no longer applies | only a missing review can be overridden, by you, with a reason that is recorded |

**Evidence is written only by `wm`**: ticks and records, and in a milestone its
roadmap lines and its Log, which change only through `wm roadmap`,
`wm new change --milestone` and `wm archive`. The planner records
its own results with `wm tick`, `wm block`, `wm gap`, `wm note` and
`wm review`. Implementers and reviewers report theirs in their last lines, and
`wm`'s hooks write the records from them. An implementer edits nothing in the
record; the one writing command it may run is `wm note`. Agents that try to write evidence by hand are
refused, and `wm check` flags evidence that doesn't follow the format. These are
guard rails against mistakes and shortcuts, not security against someone set on
getting around them. In Claude Code the agent-side rules are enforced by its
hooks; in a tool without hooks they rely on the agents following the skills.

**Commit messages** must be [conventional commits](https://www.conventionalcommits.org).
In Claude Code, its command hook refuses a `git commit` whose message isn't one,
before the commit exists, and gives the reason. When the settings list commit
scopes, only those scopes pass. A message the hook can't read, such as one
written in an editor, is allowed. Commits made by hand outside Claude Code are
not checked.

**The record's health** is checked by `wm check`. In CI it runs on every push
and pull request, through the workflow `wm ci` writes.

## Glossary

| Term | Meaning |
|---|---|
| **Record** | Everything Waymark keeps in plain markdown: the charter, specs, changes, milestones, explorations and resources. The single source of truth agents work from. |
| **Charter** | What the project is: vision, goals, non-goals, constraints and glossary, plus the facts every agent must know (Context) and the project's rules, one numbered list every agent gets at every step (Rules). |
| **Spec** | The living description of what one area of the system does. It changes only when a change is archived or synced. |
| **Requirement** | One statement in a spec of what the system SHALL do, with at least one scenario. Its heading is its key. |
| **Scenario** | A GIVEN / WHEN / THEN example of a requirement. Reviews check work against scenarios. |
| **Atlas** | A separate repository that holds the record for a project whose code spans several repositories. See the [multi-repo guide](multi-repo.md). |
| **Change** | One unit of work, from idea to archive, in its own folder: proposal, deltas, design and tasks. |
| **Proposal** | Why a change is wanted, what it changes, its non-goals and impact. Its outcome is added at archive. |
| **Delta** | A change's edits to one spec: requirements added, modified, removed or renamed. Deltas merge into the specs at archive. |
| **Design** | How a change will be built, including its decisions: the options, the choice and why. |
| **Task item** | One checkbox in a change's task list, with its criteria, how to verify it, its `- **Build:**` line, and the records of building it. |
| **Acceptance** | Your explicit approval of a change before any of it is built. Only you can give it. |
| **Tiny path** | The route for work that adds, changes or removes no requirement: no change, just your yes, a conventional commit and a pull request. |
| **Short path** | The light route for a small change: no design, and review level `self` or `none`. Marked by a `- **Path:** short` line in the proposal. |
| **Conflict** | A delta that no longer applies to its spec (a *mismatch*, which blocks its change), or two active changes that name the same requirement (an *overlap*, which is reported). |
| **Sync** | Merging an applied change's deltas into the specs without archiving it yet. |
| **Archive** | Finishing a change: its deltas merged into the specs, its outcome written, and its folder moved to a dated archive. |
| **Owner** | The one person responsible for a change. |
| **Exploration** | Saved thinking on a topic (questions, approaches, a conclusion): `open` until it leads to a change or milestone or is dropped, then archived. |
| **Resource** | The as-built facts about one thing outside the repo that the project depends on, such as a service, a platform or a dataset, in `resources/<name>.md`. A spec says what the system does and changes only through a change; a resource says what the outside world is, and is edited by hand when that world changes. See [the record](record.md#resource). |
| **Milestone** | An optional goal that several changes work toward, with a roadmap listing them, both in one `milestone.md`. A member change names it in a `- **Milestone:**` line that `wm check` holds to the roadmap, is created with `wm new change <name> --milestone <milestone>`, and its agents see the milestone's Goal and Non-goals. The roadmap changes only through `wm roadmap add`, `drop` and `move`, each recorded in the milestone's Log, and `wm close` needs every line archived. See [the record](record.md#milestone). |
| **Planner** | The main agent session, working with you: it explores, drafts, builds items or delegates them, and archives. |
| **Implementer** | A fresh agent that builds one task item with a `- **Build:** delegate` line, from the record alone. |
| **Reviewer** | A fresh, read-only agent that checks one whole change against its scenarios, design and criteria, without seeing how it was built. |
| **Review level** | How a change is checked: `self`, `independent` or `none`. Set by the `- **Review:**` line in its proposal. |
| **Log** | The last section of a change's task list, where `wm` keeps the dated records about the whole change: its acceptances, sync, reviews and any override. |
| **Finding** | One thing a review found, with a severity (`critical`, `warning` or `suggestion`), a place and a text. |
| **Context pack** | The excerpts of the record that `wm` assembles for one job: exploring, implementing or reviewing. |
| **Spec gap** | What an agent reports when the record isn't enough to do its job, instead of guessing. It goes to you. |

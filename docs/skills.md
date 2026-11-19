# Skills and agents

`wm init` installs eight **skills**, which your agent session follows when you type
a slash command, and two **agents**, fresh sessions started for one item or one
review. This page covers what each one does, the notes it reads and writes, what
it gets from `wm`, what it shows you, and when it stops. For the notes
themselves, read [The record](record.md).

- [What every skill shares](#what-every-skill-shares)
- Getting started: [`/wm-kickoff`](#wm-kickoff) · [`/wm-onboard`](#wm-onboard)
- Thinking: [`/wm-explore`](#wm-explore)
- Doing the work: [`/wm-propose`](#wm-propose) · [`/wm-update`](#wm-update) · [`/wm-apply`](#wm-apply) · [`/wm-archive`](#wm-archive) · [`/wm-pr`](#wm-pr)
- Agents: [`wm-implementer`](#wm-implementer) · [`wm-reviewer`](#wm-reviewer)

## What every skill shares

**One layout.** Every skill has the sections Role, Inputs, Steps, any sections of
its own, Quality bar, Show the human, When to stop and Rules, in that order. A
test holds the layout.

**Guidance from `wm`.** What the skills have in common comes from `wm`, so it
reads the same in every skill and every agent tool:

| Guidance | Where it comes from | What it says |
|---|---|---|
| Shared rules | every `wm instructions` output | Only you accept a change or archive past a missing review; only `wm` writes records; specs change only by archive or sync; never guess; nothing is pushed, opened as a pull request or merged without your yes. |
| Checklist | `wm instructions` at propose, specs, design and tasks | What must hold before moving on. A check marked `wm` is enforced by `wm check`; the agent judges the rest. |
| Writing rules | the specs step | One behavior per requirement, with SHALL; what a user sees, not how it's built; a scenario for the usual case and each refusal or boundary; one action per WHEN, a checkable THEN. |
| Sizing rules | the tasks step | One item per slice that can be built and verified alone; split past about five criteria; docs and skills get their own item; the record stays healthy after each tick. |
| Severity rubric | the review pack, and `wm instructions` at review | **Critical:** a criterion or scenario doesn't hold, the code breaks a requirement, or a check fails. **Warning:** all holds, but an edge is untested, something is met by accident, or a likely next change breaks it. **Suggestion:** clarity, naming or duplication. The higher when torn. |
| Stopping rules | the implement pack | `spec-gap` when the record leaves a choice open; `blocked` for a cause outside the item; `partial` after three attempts at the same failing check; other work goes in a note. |
| The charter | every context pack | The project's Context, and the Rules for that step only. |

**Guard rails.** In Claude Code, hooks hold what matters most: agents can't run
`wm accept` or the archive override, commit messages must be conventional with an
allowed scope, a delegated implementer edits only its item's code, and a reviewer
edits nothing.

---

## `/wm-kickoff`

Turns what you know about the project into a charter every later agent can work
from, and settles the settings. **Use it** right after `wm init`, or while the
charter is still a skeleton.

**How it works**

1. Reads `wm status`, the charter and `config.toml`, and asks whether to revise a
   filled-in charter instead of starting over.
2. Interviews you one charter section at a time: Vision, Goals, Non-goals,
   Constraints, Glossary. Each answer is written in before the next question.
3. Reads the repository for Context (layout, build and test commands,
   conventions), states what it found, and asks you to correct it.
4. Asks for the project's rules, as one numbered list in Rules.
5. Settings: confirms the default review level, offers commit scopes, and in an
   atlas adds the repos and runs `wm atlas register` and `wm atlas doctor`.
6. Runs `wm check`, shows you the charter, and revises until you approve.

| Reads | Writes |
|---|---|
| `wm status`, `charter.md`, `config.toml`, the repository | the charter (numbered goals and constraints, a bullet glossary, Context, Rules); `config.toml` |

**Shows you** each section as it drafts it, then the whole charter and the
settings it changed. **Stops** when you approve (then offers `/wm-onboard`), when
you want to stop partway, or leaves a question in its section when only you can
answer it later.

## `/wm-onboard`

Runs one real, small change through the whole workflow on your own code, saying
in a sentence or two what each step is for before it happens. There is no demo
project; the change stays. **Use it** after kickoff, or when someone is new to
Waymark.

**How it works:** picks with you something small and real; follows `/wm-propose`
(on the short path if it fits), explaining the paths, deltas and items; asks you
to run `wm accept`; follows `/wm-apply`; shows `wm status`, `wm show` and
`wm inbox`; follows `/wm-archive`; and wraps up with the skills you'll use from
then on.

**Writes** one real change and the specs its delta creates, through the skills it
follows. **Stops** when you want to stop (`wm status` shows where to resume), when
the change turns out tiny (it follows the tiny path of `/wm-propose` instead), or once the change is
archived.

## `/wm-explore`

Helps you get from a fuzzy idea to a clear one, from the record. It writes
nothing until you pick one of its closing offers. **Use it** when an idea is
still fuzzy, or you don't know yet whether it's a change. **Pick up** a saved
exploration with `/wm-explore <exploration>`.

**How it works**

1. **A saved exploration:** when you name one, or the idea matches one and you
   say it is that one, it reads it with `wm show`, says what in the record has
   changed since, and goes on from its Questions and Approaches.
2. **What the record says:** the specs, changes in flight, milestones, saved
   explorations and resources that bear on the idea, and which requirements it
   would touch.
3. **The problem:** what it solves, and for whom.
4. **The questions:** it answers what the record or the code can, and leaves the
   rest for you.
5. **The approaches:** two or more, each with what speaks for and against it,
   and its cost.
6. **A recommendation,** and what would change it.
7. **The closing offers,** four of them:
   - for a new idea: do nothing; save an exploration; start a proposal, of any
     size; start a milestone;
   - for a saved exploration: do nothing; update it, or drop it with
     `wm exploration drop`; start a proposal; start a milestone. The proposal
     and the milestone are created with `--from <exploration>`.

| Reads | Writes, only on an offer |
|---|---|
| `wm context --for explore`; `wm show <spec\|change\|exploration>`, with `--from <atlas>` for a referenced atlas; `wm show <name> --kind resource`; the code, without changing it | an exploration through `wm new exploration`, or its sections; `wm exploration drop`; or a milestone with its Goal, created with `--from` when it comes from an exploration, and its Roadmap lines through `wm roadmap add` |

**Stops** when you pick an offer (it does that one only), when you want to stop
(it makes the offers), or when the idea is already in flight or in the specs.

## `/wm-propose`

Does a piece of work, whatever its size. It looks at the specs and the code to
see what the work involves, and the path follows from that. **Use it** for
anything you want built or changed, from a typo to a new feature.

**How it works**

1. **Look at the work:** it's tiny when no requirement changes, short when the
   specs change and nothing is left to settle, and full otherwise.
2. **The tiny path:** shows one line, `Tiny: <what it will change>; keeps <the
   requirement>`, and builds nothing until you say yes. Then it branches, builds
   only what it said, runs the checks, the full checks and `wm check`, commits
   with a conventional message, and offers a pull request it describes itself.
   It writes nothing to the record. If the work turns out to change a
   requirement, it stops building and drafts a change.
3. **Questions:** lists what the record and your words don't settle (scope,
   edges, names, what's out) and asks you, each with the answer it recommends.
   A question still open puts the change on the full path, under the design's
   Open questions, which block acceptance until you answer.
4. **Name:** a kebab-case name starting with a verb; `wm new change <name>`.
5. **Drafting, step by step,** with `wm instructions` at each: the template, the
   guidance with its writing and sizing rules, and the checklist. `wm check`
   after each step.
6. **Proposal**, then **deltas**, then the **design** (decisions with their
   status and who made them), then the **tasks**.
7. Suggests the **review level** and which items to **delegate**.
8. **Consistency check:** `- **Specs:**` matches the deltas, every scenario is
   covered by an item, the design covers every requirement and adds none, the
   tasks touch what `- **Code:**` names, and each choice is what the approach does.
9. Shows the **acceptance summary** and asks you to run `wm accept`.

| Reads | Writes |
|---|---|
| your request; `wm status`; `wm context --for explore`; `wm show <spec>`; the code; `wm instructions --change <name>` | tiny: code only, never the record; a change: `proposal.md`, `specs/<area>.md` deltas, `design.md` (full path), `tasks.md` |

**Shows you** what the work involves first. For tiny work, the `Tiny:` line, then the
pull request's title, description and target. For a change, each draft in a few
lines; before acceptance: what it does, the deltas per spec, each decision with
who made it, the review level, and the items with which to delegate. **Stops**
when you say no to tiny work, once its pull request is open (it never merges),
when an answer changes the scope, when a decision only you can make comes up,
and at accept, which only you do.

## `/wm-update`

Revises a change that already exists. Every edit is confirmed by you first,
along with whether it withdraws acceptance. **Use it** for a spec gap, a
conflict, a decision to settle, a review's findings or a change of scope.

**How it works:** finds out what needs to change and why; tells you whether each
edit withdraws acceptance (editing the proposal, a delta, the design or an
accepted item does; adding an item or a note doesn't); makes each edit only after
your yes; works through the revised steps' checklists and runs `wm check`; asks
you to accept again if acceptance was withdrawn.

**Common cases**

| Case | What it does |
|---|---|
| A spec gap | Writes your answer into the delta or the item's criteria; then `wm resolve`. |
| A conflict | Rewrites the delta against the spec as it now reads. |
| A decision to settle | `- **Status:** decided` and `- **Decided by:** human`; `None.` once no question is left. |
| The Impact out of step | Updates `- **Specs:**` to match the deltas. |
| A rename | A RENAMED section; MODIFIED under the new name to change the text too. |
| New work | Appends new items; never renumbers. |

**Writes** any of the change's notes, edit by edit, and `wm resolve` or `wm note`
records, with `--by` when you decided. **Stops** when you decline an edit, when a
decision only you can make comes up, when the revision grows into new behavior
(it offers a new change instead), and when acceptance was withdrawn.

## `/wm-apply`

Builds an accepted change item by item, itself or through an implementer for a
delegated item, commits each one, then reviews the whole change once at its level
and handles the verdict. **Use it** when a change is accepted and ready to build.

**How it works**

1. Checks the step, and gets on the change's branch (in an atlas, every repo's).
2. **Apply:** for an item it builds itself, reads the item's context pack
   (`wm context <change> <item> --for implement`), builds exactly that item, runs
   its verification, then records `wm tick`, `wm block` or `wm gap`.
3. A delegated item goes to `wm-implementer` with exactly `<change> <item>`; its
   ending is recorded by `wm`.
4. **Commits** each ticked item with a conventional message.
5. **Review:** a self-review against every scenario, the design and every
   criterion, with findings graded by the severity rubric, recorded with
   `wm review --self`; or `wm-reviewer` with exactly `<change>` when the level is
   independent. An item added after a passing review gets a review of its own,
   of the items no passing review covers.
6. A `changes` verdict reopens the named items to rebuild; a second one, or a
   spec gap, goes to you.
7. **Resolve-items:** brings each blocker, gap or verdict to you, then
   `wm resolve`.

| Reads | Writes |
|---|---|
| `wm instructions --change <name>`; each item's context pack; `wm show` after an agent returns | code, one commit per item; ticks; in the Log, `(blocked)`, `(gap)` and `(note)` naming their item, `(self-review)` or `(review)`, and `(resolved)` |

**Shows you**, after each item, what was built, the checks and their result, and
the commit; after the review, the verdict and each finding. **Stops** when the
change isn't ready, when blocked items leave nothing else to do, on a second
`changes` verdict or a spec gap, and when the step is archive (it offers
`/wm-archive`).

## `/wm-archive`

Completes a change on its branch, before its pull request: the deltas merge into
the living specs, the outcome is written, and the folder moves to the dated
archive. It is your decision. **Use it** when every item is built and the change
is reviewed.

**How it works:** checks the step is archive and the work is committed, and asks
you; drafts the outcome with you (what was built, and how it differs from the
proposal); runs, or asks you to run,
`wm archive <change> --built "…" --differs "…"`; runs `wm check` and `wm status`;
asks whether the milestone's roadmap still fits, changing it with `wm roadmap`,
and whether the milestone is ready to close; commits the record on the branch;
offers `/wm-pr`.

| Reads | Writes |
|---|---|
| `wm instructions`; `wm show <change>`, for the outcome | the specs, through the merge; `## Outcome` with `- **Built:**` and `- **Differs:**`; the change folder moved to `changes/archive/`; through `wm archive`, the milestone's Roadmap line and an `(archived)` record in its Log |

If the archive is refused for an unaccepted change, unticked items or a conflict,
it goes back to `/wm-apply` or `/wm-update`; a missing review only you may
override. If the pull request needs more work, it reverts the archive commit and
archives again once the work is done.

## `/wm-pr`

Opens a pull request described from the change, only when you ask, showing you
the text first. **Use it** once a change's work is committed, usually archived on
its branch.

**How it works:** checks the work is committed (and offers `/wm-archive` first if
it isn't archived); runs `wm pr <change>` for the title and description, once per
repo in an atlas with `--repo`; shows you the title, the description and the
target branch; only on your yes, pushes and opens it with your git host's tool;
gives you the link.

**Writes** nothing in the record. **Stops** if you say no, and never merges.

---

## `wm-implementer`

A fresh agent that builds one item marked `- **Build:** delegate`, from the record
alone. `/wm-apply` starts it with exactly `<change> <item>` for a large item,
parallel work, or a cold check that the record is enough to build from.

**How it works:** runs `wm context <change> <item> --for implement` (a refusal
ends it as `blocked`); reads the whole pack; builds exactly the item, so its
criteria hold and the scenarios pass; runs the item's verification; stays inside
its item (in an atlas, its item's repo), putting other work in a `wm note`; stops
by the stopping rules; ends with two lines:

```text
ITEM: <change> <item>
RESULT: <done | partial | spec-gap | blocked>: <a short note>
```

| Reads | Writes |
|---|---|
| the implement pack: the item and its criteria, the proposal, deltas, design, the requirements touched as they stand, the resources that serve their specs, Context, the project's rules, the stopping rules | code in its item's repo; `wm note --by wm-implementer`, the one writing command it may run; its ending, which `wm` records as a tick, `(blocked)`, `(gap)` or `(note)` |

## `wm-reviewer`

A fresh agent that checks one whole change against what was agreed, read-only,
without seeing how it was built. `/wm-apply` starts it with exactly `<change>`
when the review level is independent.

**How it works:** runs `wm context <change> --for review` (a refusal ends it as
`spec-gap`); finds where each item was built; runs each item's verification and
the tests, read-only; checks that the change is complete (every criterion holds,
every scenario is met), correct (at the edges too) and coherent (it follows the
design, and the items fit together); checks that an earlier review's requested
changes were made; grades each finding by the severity rubric; ends with:

```text
FINDING: <critical | warning | suggestion>: <place>: <what is wrong>
CHANGE: <change>
VERDICT: <pass | changes <item>... | spec-gap>: <reasons>
```

| Reads | Writes |
|---|---|
| the review pack: the items to review (every item, or those no passing review covers) with their criteria, verification and location, the deltas, the resources that serve their specs, the design, earlier reviews and resolutions, Context, the project's rules, the severity rubric; the code | nothing: `wm` records its ending as a `(review)` record with each finding under it; a `changes` verdict reopens the items it names; `wm` refuses a pass with a critical finding |

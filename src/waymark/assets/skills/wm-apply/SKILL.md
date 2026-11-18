---
name: wm-apply
description: Build an accepted Waymark change item by item - build each item yourself or delegate it to an implementer when it is tagged so, commit it, then review the whole change once and handle the verdict. Use when a change is accepted and ready to build.
---

# Apply

## Role

You are the planner. You build each item yourself, from the record, unless the item has a `- Build: delegate` line: then a fresh implementer that sees only the record builds it. Either way the record is the source of truth. Once every item is built, the whole change is reviewed once, at its review level. You build or delegate, record, commit and review.

## Inputs

- The change's name. If the human didn't name it, run `wm ls changes` and ask which one.
- `wm instructions --change <name> --json`: the step, the item, who builds it, and the commands.
- For an item you build, `wm context <name> <item> --for implement`.

## Steps

1. Run `wm instructions --change <name> --json`. The step must be `apply`, `review`, `resolve-items` or `archive`; otherwise see When to stop.
2. Make sure you are on the change's branch: its name is the branch name. Create it if it doesn't exist. In an atlas, the same branch name is used in the atlas and in every code repo the change's items name; `wm status` shows each one's branch and warns when one differs. If `wm` says a repo isn't on this machine, ask the human to clone it and run `wm atlas register`.
3. Run the loop below until `wm instructions --change <name> --json` says the step is `archive`.
4. When the step is `archive`, every item is built and the change is reviewed. Tell the human, and offer the `wm-archive` skill, which archives the change on its branch, and then the `wm-pr` skill.

## The loop

### Step `apply`

- If the commands start with `wm reopen`, run it first: a review of the change named this item to rebuild. Read what the review found with `wm show <name>` before you start.
- `wm instructions` says who builds the item. An item without a `- Build: delegate` line, you build yourself; one with it, you delegate.

**An item you build yourself.**

1. Run `wm context <name> <item> --for implement` and read the whole pack: the item and its criteria, the proposal, the deltas, the design, the requirements they touch, and the project's rules for this step.
2. Build exactly what the item asks for, so that its criteria hold and the scenarios in the deltas pass. Stay inside the item; other work you notice belongs to another item or a revision. In an atlas, edit only the code repo the item names.
3. Build only on what the record says. If you rely on a fact that isn't written down, such as something the human said in this session, write it into the record first: a revision with the `wm-update` skill, or `wm gap` if the human must decide.
4. Run the verification the item names and the checks the item touches, and follow the project's rules for this step from the pack.
5. Record the result:
   - the criteria hold: `wm tick <name> <item>`;
   - something outside the item stops you: `wm block <name> <item> "<reason>"`;
   - the record isn't enough to build it: `wm gap <name> <item> "<what is missing>"`.

**An item with `- Build: delegate`.**

- Start the `wm-implementer` agent with a prompt of exactly `<name> <item>` and nothing else, for example `add-search-limit 1.2`. It builds its own context from the record.
- When it returns, run `wm show <name> --json` and look at the item:
  - ticked: commit it and go on;
  - an open `(blocked)` or `(gap)` record under it: that item waits on the human; go on to the next step;
  - neither, and the agent reported `partial`: delegate the item again;
  - neither, and your tool recorded nothing: record the result yourself with `wm tick`, `wm block` or `wm gap`, using the agent's own words.

A blocked item, or one with a spec gap, waits on the human; go on to the next step.

### After an item is ticked

Commit the item's work, in the repository it belongs to, with a conventional commit message such as `feat(api): add the result limit`. If the project lists commit scopes, use one of them or none. When a git hook stops the commit, fix what it says; don't skip the hooks.

### Step `review`

Once every item is ticked, the change is reviewed once, as a whole. `wm instructions` tells you which kind; the change's review level comes from its proposal.

An item added after a passing review is reviewed on its own. Once it is ticked, `wm instructions` makes the next step a review of the items no passing review covers, at the change's level, and names them. Review just those, and how they fit the rest. `wm` writes the record with `covers <item>...`, naming the items the review was of.

- **Self-review.** Review the change against its deltas' scenarios, its design and each item's criteria:
  - complete: every criterion holds, and every scenario is met by some item;
  - correct: the code does what the requirements say, at the edges too;
  - coherent: it follows the design, and the items fit together.

  Read the code, run each item's verification, and run the project's full checks. Then record it with `wm review <name> --self "<summary>"`, adding a `--finding "<critical|warning|suggestion>: <place>: <text>"` for each thing you found, graded by the severity rubric `wm instructions` gives at the review step. A critical finding means it isn't done: fix it, or record `wm verdict <name> changes "<reasons>" --items <item>...` to rebuild the items it names.
- **Independent review.** Start the `wm-reviewer` agent with a prompt of exactly `<name>` and nothing else. It ends with `CHANGE:` and `VERDICT:` lines, and `wm` records the verdict and its findings. When it returns, look at the change with `wm show <name>`:
  - `pass`: the change is reviewed;
  - `changes`: the items it names are reopened and built again, then the change is reviewed again, independently;
  - a second `changes`, or `spec-gap`: it goes to the human.
  If your tool recorded nothing, run `wm verdict <name> <verdict> "<the reviewer's reasons>" --by wm-reviewer` with the reviewer's own words, its `--items` and its `--finding` lines.
- **Level `none`.** No review is needed; the step is skipped.

Commit the review record once it is written.

### Step `resolve-items`

Only what waits on the human is left. Run `wm inbox` and bring each one to them: the blocker, the spec gap, or the verdict. A spec gap is fixed by revising the change with the `wm-update` skill. When the fix, or a review, only needs more work and no change to the deltas or the design, add a new item through the `wm-update` skill, with the human's confirmation: it keeps the acceptance, and is built like any other. Once they have decided, run `wm resolve <name> <item> "<what was decided>"` for an item, or `wm resolve <name> review "<what was decided>"` for the change's review.

### What `wm` writes

Every line `wm` writes is a dated record, `(kind) YYYY-MM-DD [<args>] [by <who>]: <text>`. Records about one item sit under it: `(blocked)`, `(gap)`, `(note)`, `(reopened)` and `(resolved)`. Records about the whole change sit in the `## Log` at the end of the task list: `(accepted)`, `(synced)`, `(self-review)`, `(review)`, `(resolved)` and `(override)`. Records are never edited or removed; a later one supersedes an earlier one, so `wm resolve` adds a `(resolved)` record and the blocker stays.

- Leave a note on an unfinished item with `wm note <name> <item> "<text>"`.
- `by` is your git name. Pass `--by "<name>"` to any writing command when someone else did the work, such as `--by wm-reviewer` when you record a reviewer's verdict for it.
- `wm check --fix` puts the record in its standard layout when the human asks; it never changes wording.

## Quality bar

- Each item's criteria hold, and its verification ran and passed.
- Nothing was built on a fact the record doesn't hold.
- Each ticked item is committed on its own, with a conventional message.
- The review checked every scenario, the design and every item's criteria, and recorded each finding.

## Show the human

After each item:

- **Item:** its number and title.
- **Built:** what changed, in a sentence or two.
- **Checks:** what ran, and the result.
- **Commit:** its hash and message.

After the review: the verdict, and each finding with its severity and place. When the step is `archive`, say so and offer `wm-archive`.

## When to stop

- The step is not `apply`, `review`, `resolve-items` or `archive`: the change isn't ready. Say what the step is and stop.
- An item is blocked or has a spec gap and nothing else can go on: it waits on the human.
- A second `changes` verdict, or a `spec-gap` verdict: it goes to the human.
- The step is `archive`: offer `wm-archive` and stop.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Whoever builds an item builds it from the record; what isn't written there gets written there first.
- Start an implementer with the change and item only, and a reviewer with the change only. Don't explain the task in the prompt: what they need is in the record, and if it isn't, that is a spec gap.
- Record a reviewer's verdict in the reviewer's words, never your retelling.
- If your tool has no isolated agents, build a tagged item yourself as you would an untagged one. A change that needs an independent review then needs the human, or another session that didn't build it, to review it.

# The record

Everything Waymark keeps lives in plain markdown in `waymark/`, committed with
your code. This page covers each kind of note: what it's for, its sections, the
lines it can hold, who writes and updates it, and what `wm check` holds it to.
For how the notes fit into the workflow, read [Concepts](concepts.md).

- [Two kinds of line](#two-kinds-of-line)
- [Settings](#settings-configtoml) · [Charter](#charter-chartermd) · [Spec](#spec-specsareamd)
- [Proposal](#proposal) · [Delta](#delta) · [Design](#design) · [Task list](#task-list)
- [Milestone](#milestone) · [Exploration](#exploration) · [Resource](#resource)
- [Records](#records) · [What holds it together](#what-holds-it-together)

```text
waymark/
  config.toml
  charter.md
  specs/<area>.md
  changes/<change>/
    proposal.md
    specs/<area>.md       deltas
    design.md             full path only
    tasks.md              items, then ## Log
  changes/archive/YYYY-MM-DD-<change>/
  milestones/<name>/milestone.md
  milestones/archive/YYYY-MM-DD-<name>/
  explorations/<name>.md
  resources/<name>.md
```

Each of the seven folders, `specs/`, `changes/`, `changes/archive/`,
`explorations/`, `milestones/`, `milestones/archive/` and `resources/`, holds an empty
`.gitkeep`, so git keeps it while it holds nothing else. `wm init` writes them
with a new record, and `wm update` adds any that are missing. No `wm` command
removes one, and `wm check` doesn't read them.

## Two kinds of line

- **What people and agents write** is sections of prose and `- Label:` lines,
  such as `- Owner: Sam Doe` or `- Criteria: at most fifty results`.
- **What `wm` writes** is a dated record of one shape,
  `(kind) YYYY-MM-DD [<args>] [by <who>]: <text>`, such as
  `(blocked) 2026-01-16 by wm-implementer: the index service is down`. Only `wm`
  writes records, and none is ever edited or removed. See [Records](#records).

Every template carries a short good and bad example in a comment. Comments are
left out of what `wm check` reads and out of the acceptance fingerprint, so you
can delete them without consequence.

## Settings: `config.toml`

The project's settings, in TOML. `wm init` writes it with comments; you edit the
values and keep the keys.

| Key | What it holds |
|---|---|
| `wm_version` | The exact wm version the project uses. Any version can read the record; only this one may write it. |
| `record_format` | The record's format, now `1`. Never edit it by hand. A record in another format is refused, with the reason to install the `wm` version that wrote it. |
| `default_review` | `self`, `independent` or `none`: a change's review level when its proposal has no `- Review:` line. |
| `agent_tools` | Which agent tools get skills, agents and hooks, such as `["claude-code"]`. |
| `commit_scopes` | Optional. The scopes a conventional commit may use; the commit hook refuses any other. |
| `[atlas.repos.<name>]` | In an atlas, one table per code repo, with a relative `path` hint. |
| `[references.<atlas>]` | Another atlas whose specs this project reads, read only, with `wm show <spec> --from <atlas>`. |

**Written by** `wm init`, then you or `/wm-kickoff`. **Checks:** `invalid-setting`, `unknown-setting`.

## Charter: `charter.md`

What the project is, and the facts and rules every agent works from. Its Context
goes into every context pack, and each step's agent gets only that step's Rules.

| Section | What goes in it |
|---|---|
| `## Vision` | What the project is, for whom, and why now. |
| `## Goals` | A numbered list, `1. <goal>`, counted from 1, so a change can cite a goal by number. |
| `## Non-goals` | What it leaves out that someone might expect. |
| `## Constraints` | A numbered list: platforms, dependencies, budgets, what must never happen. |
| `## Glossary` | One term per line: `- **<term>**: <meaning>`. |
| `## Context` | Where things live, how to build and test, who owns what. |
| `## Rules` | One capitalized heading per step (`### Explore`, `### Propose`, `### Specs`, `### Design`, `### Tasks`, `### Apply`, `### Review`, `### Archive`). A step with no rules may leave its heading out. |

An indented line under a numbered item continues it. **Written by**
`/wm-kickoff` with you; it isn't changed through a change.
**Checks:** `missing-section`, `numbered-list-format`, `glossary-format`,
`old-layout` (a `Term: meaning` glossary line), `unknown-step`, `duplicate-section`.

```markdown
## Goals

1. Agents work only from what is written down.
2. Every review is recorded with its change.

## Glossary

- **Record**: everything Waymark keeps in waymark/.
```

## Spec: `specs/<area>.md`

A living spec says what one area of the system does today, as a user or another
program sees it. **It is never edited by hand:** it changes only when a change's
deltas merge into it, at archive or with `wm sync`. A spec is born the first time
a change adds a delta for a new area.

| Part | What it holds |
|---|---|
| `# <Title>` | The spec's name. In an atlas, an optional `Repos: api, web` line follows. |
| `## Purpose` | What the area is for. |
| `## Background` | Optional. Facts about the area that aren't requirements and can't be found in the code. It changes only through a delta. |
| `## Requirements` | Every requirement, each under `### Requirement: <name>`. The name is the key, matched ignoring case and spacing. |
| Requirement | A statement that says `SHALL`, then one or more `#### Scenario: <name>` blocks. |
| Scenario | `- GIVEN` a starting state (optional), `- WHEN` one action, `- THEN` an outcome someone else can check. |

**Checks:** `requirement-without-shall`, `requirement-without-scenario`,
`scenario-incomplete`, `scenario-format`, `duplicate-requirement`, `unknown-repo`,
`empty-section` (an empty Purpose or Background).

```markdown
### Requirement: Result limit
A search SHALL return at most fifty results, best matches first.

#### Scenario: Many matches
- GIVEN an index with fifty-one matches
- WHEN a search runs
- THEN fifty results come back
```

## Proposal

`changes/<change>/proposal.md`. Why a change is wanted and what it changes.
Created by `wm new change <name>` (with `--short` for the short path,
`--milestone <milestone>` for a change in a [milestone](#milestone), and
`--after <change>` for a change based on another's branch), drafted by
`/wm-propose` and revised by `/wm-update`. Acceptance covers everything in it
except the Outcome.

| Part | What it holds |
|---|---|
| Facts under the title | `- Owner: <name>` (from git), and optionally `- Milestone: <name>`, `- After: <change>`, `- Review: self\|independent\|none` and `- Path: short`. |
| `## Why` | The problem and why now, not the solution. |
| `## What changes` | What will be different once the change is archived. |
| `## Non-goals` | What a reader might expect and won't get. |
| `## Impact` | Three lines, each with text or nested bullets: `- Specs:`, `- User-visible:`, `- Code:`. |
| `## Outcome` | Written by `wm archive`: `- Built: <text>` and `- Differs: <text>` (`none` when nothing differs). |

- **`- Specs:`** names each spec the change has a delta for, in backticks, such
  as ``- Specs: `search` (modified)``, or says `- Specs: none`, the only way to
  skip the specs step. A spec named without a delta sends the next step back to
  the specs; a delta whose spec isn't named is reported on the proposal.
- **`- User-visible:`** lists the commands, output, files and formats users will
  see change, for the changelog.
- **`- Code:`** names the parts of the code it touches, and in an atlas the repos.
- **`- Review: independent`** is for a change that modifies or removes an existing
  requirement, or touches security, data integrity or money; `wm check` warns
  when such a change is reviewed below independent.

**Checks:** `missing-owner`, `invalid-path`, `invalid-review-level`,
`impact-format`, `impact-mismatch`, `old-layout`, `short-path-review`, `empty-section`.
For an `- After:` line in an active change: `unknown-after` (no active or archived
change has that name), `after-self`, `after-cycle` (the lines lead back to the
change), all errors, and the warning `after-merged` (the change it comes after is
archived or merged, so rebase onto the default branch and take the line off). See
[Branches](concepts.md#branches).

## Delta

`changes/<change>/specs/<area>.md`. One change's edit to one spec. It names only
what it adds, modifies, removes or renames. Archiving or syncing merges it into
the living spec, renames first.

| Section | What goes in it |
|---|---|
| `# <Spec title>` | The spec it edits; a `Repos:` line may follow in an atlas. |
| `## Purpose` | Only when the delta creates the spec, or changes what it is for. |
| `## Background` | Only when the change sets the spec's Background. At archive or sync it replaces the spec's Background whole, or is added before `## Requirements` when the spec has none. |
| `## ADDED Requirements` | New requirements, each with its scenarios. |
| `## MODIFIED Requirements` | Each written out in full as it should read afterwards, under its heading in the spec, or its new name when also renamed. |
| `## REMOVED Requirements` | Each heading with a `Reason:` line. |
| `## RENAMED Requirements` | A `- From: <old name>` line, then a `- To: <new name>` line. The requirement keeps its text. |

A delta that no longer applies, because another change was archived first, is a
**conflict**; `/wm-update` rewrites it against the spec as it now reads. The
fingerprint covers the living text of every requirement a delta touches, so
another change archiving into the same requirement withdraws this one's acceptance.

**Checks:** `empty-delta`, `delta-without-purpose`, `removal-without-reason`,
`malformed-rename`, `delta-requirement-missing`, `delta-requirement-exists`, `old-layout`,
`empty-section` (an empty Purpose or Background).

## Design

`changes/<change>/design.md`, on the full path only. How the change will be
built, and every decision with its options, choice and reason. **A decision still
proposed, or a question still open, keeps the change from acceptance:** the next
step stays at design, and `wm accept` refuses, naming each one.

| Section | What goes in it |
|---|---|
| `## Context` | What the code looks like today where the change lands. |
| `## Approach` | How it will be built, in enough detail to split into items. How, not what. |
| `## Decisions` | One `### Decision: <name>` per choice that had real options. |
| `## Open questions` | A list of what is still undecided, or `None.` |
| `## Risks and trade-offs` | What could go wrong, and what was given up. |

Each decision holds these lines:

| Line | Meaning |
|---|---|
| `- Status: proposed\|decided` | Proposed until you settle it. |
| `- Decided by: human\|planner` | Human only where you made the call. |
| `- Options:` | At least two: bullets under it, or one line joined by "or" or ";". |
| `- Choice:` | The one taken. |
| `- Why:` | The reason. |

**Checks:** `decision-incomplete`, `decision-format`, `decision-options`,
`missing-section`, `open-questions-format`, `short-path-design`.

## Task list

`changes/<change>/tasks.md`. The items that build the change, each small enough
to build from the record alone, then a `## Log` where `wm` records the acceptance,
syncs and reviews.

- **Sections** are numbered, `## 1. <title>`.
- **Items** are `- [ ] 1.1 <title>`, numbered by section and never renumbered;
  new items are appended. Only `wm tick` ticks one.
- **Lines under an item:**

  | Line | Meaning |
  |---|---|
  | `- Criteria:` | What must be true. Several go as a nested list, one per bullet. Required. |
  | `- Verify:` | How to check it. May be a nested list too. Required. |
  | `- Repo: <name>` | In an atlas, the code repo it works in. Required there. |
  | `- Build: delegate` | Send it to a fresh implementer agent. The only value. |

- **Records under an item**, written by `wm`: `(blocked)`, `(gap)`, `(note)`,
  `(reopened)`, `(resolved)`.
- **`## Log`**, always last, written by `wm`: `(accepted)`, `(synced)`,
  `(self-review)`, `(review)`, `(resolved)`, `(override)`. A review's findings sit
  under it as ``- <severity> `<place>`: <text>``.

The acceptance names the items it covers: **adding** an item keeps it, while
**changing** or removing an accepted item withdraws it.

**Checks:** `item-incomplete`, `item-number`, `section-number`,
`item-without-repo`, `unknown-build-tag`, `log-section-last`, `misplaced-record`,
`malformed-finding`, `changes-without-items`.

```markdown
- [x] 1.1 Cap the result count
  - Criteria:
    - at most fifty results come back
    - they are the best matches
  - Verify: a test with fifty-one matches
  - (note) 2026-01-15 by Sam Doe: the cap sits after sorting

## Log

- (accepted) 2026-01-15 fingerprint 6cec39a287bf99f2 items 1.1 by Sam Doe
- (self-review) 2026-01-16 covers 1.1 by Sam Doe: every criterion holds
  - suggestion `docs/search.md`: name the limit in the help text
```

## Milestone

`milestones/<name>/milestone.md`. A goal several changes work toward, and the
roadmap that lists them, in one file. Created by `wm new milestone <name>`.

| Section | What goes in it |
|---|---|
| `## Goal` | What the milestone achieves. |
| `## Done when` | How anyone can tell it has been reached. |
| `## Non-goals` | What it leaves out. |
| `## Roadmap` | One list line per change. Only lines here, outside comments, are roadmap entries. |
| `## Log` | Optional, always last, written by `wm`: a record for each change to the plan. |

A change not proposed yet is a plain line, such as `- add-cache: cache hot
queries`; a proposed one links to its proposal. Archiving a change ticks its
line and rewrites the link, and `wm status` counts the progress.

You change the roadmap only through `wm`. An agent's edit that adds, changes or
removes a roadmap line or a Log record is refused; edits to the other sections
are allowed.

| Command | What it does |
|---|---|
| `wm roadmap add <milestone> <change> "<description>"` | Adds `- <change>: <description>` at the end of the roadmap. Refused for a name already on it. |
| `wm roadmap drop <milestone> <change> --reason "<why>"` | Removes the change's line. Refused for an active change whose proposal names the milestone: take its `- Milestone:` line off first. |
| `wm roadmap move <milestone> <change> --after <change>` | Moves the line right after another's, or to the top with `--first`. |

Each change to the plan writes a record in the milestone's `## Log`, which `wm`
creates at the end of the file the first time:

```
(added) 2026-11-20 add-cache by Ada: cache hot queries
(moved) 2026-11-20 add-cache first by Ada
(proposed) 2026-11-21 add-limit by Ada
(dropped) 2026-11-21 add-cache by Ada: the index is fast enough
(archived) 2026-11-22 add-limit by Ada
```

`(proposed)` comes from `wm new change --milestone`, and `(archived)` from
`wm archive` when the change's proposal names the milestone. Lines already on a
roadmap before its Log began have no records.

`wm close <milestone>` moves it to `milestones/archive/YYYY-MM-DD-<name>/` once
every line on its roadmap links to an archived change, and rewrites links to
it. A planned line keeps it open until it is proposed, or dropped with a reason.

A change belongs to a milestone when its proposal has a `- Milestone: <name>`
line, naming the milestone's folder, and the milestone's roadmap links the
proposal. A change without the line belongs to no milestone.

- **Creating one:** `wm new change add-cache --milestone faster-search` writes
  `- Milestone: faster-search` in the proposal. In the roadmap, it turns the
  plain line `- add-cache: cache hot queries` into a link to
  `../../changes/add-cache/proposal.md` that keeps the text after the name, or
  adds a linked line at the end when there is no such line. A milestone that
  isn't active is refused.
- **Its agents:** the implement and review context packs of a member change
  carry the milestone's name, Goal and Non-goals, not its Done when or roadmap.

**Checks:** `milestone-file` (a leftover `goal.md` or `roadmap.md`),
`missing-file`, `section-order`, `missing-section`, `log-section-last` (a
`## Log` that isn't the last section). On an active change's
proposal: `unknown-milestone` (no active milestone has that name),
`milestone-unlinked` (the named milestone's roadmap doesn't link the change),
`milestone-missing` (a roadmap links the change, and the proposal names no
milestone), `milestone-other` (the proposal names one milestone, and another's
roadmap links it), `milestone-twice` (more than one roadmap links it). Archived
changes aren't checked against roadmaps.

## Exploration

`explorations/<name>.md`. Saved thinking about an idea that isn't a change yet.
Created by `wm new exploration <name>`, written by `/wm-explore` when you pick
that offer.

- **`- Status:`** under the title says where it stands: `open`, `parked`, or
  `led-to <link>` to the change or milestone it led to. Only this line decides it.
- **Sections:** Context, Questions, Approaches, Conclusion (empty while open; the
  reason when parked), Related.

**Checks:** `missing-status`, `unknown-status`, `parked-without-reason`.

## Resource

`resources/<name>.md`. The as-built facts about one thing outside the repo that
the project depends on: a service it talks to, a platform it runs on, an account
it signs in with, a database, a dataset or a document. Created by
`wm new resource <name> <kind>`, listed by `wm ls resources` and shown by
`wm show <name> --kind resource`.

**Never store a secret in a resource**: no passwords, keys, tokens or connection
strings. Say where the secret lives instead. `wm` doesn't scan for secrets.

One resource covers one account or one separate deployment. The environments of
one deployment, such as dev and prod, are `###` subsections inside its sections.

| Line | What it holds |
|---|---|
| `- Kind:` | `service`, `platform`, `account`, `database`, `dataset` or `document`. |
| `- Serves:` | The specs it serves, separated by commas, or `none`. |
| `- Status:` | `active`, or `retired` once nothing uses it. |
| `- Verified:` | The day its facts were last checked, written `YYYY-MM-DD`. |

| Section | What goes in it |
|---|---|
| `## What it is` | What it is, who runs it and what the project uses it for. |
| `## Access` | How to reach it, and where its secrets live. |
| `## Interface` | How the code talks to it: endpoints, formats, ids, limits, quirks. |
| `## Data` | What it holds or returns that the project relies on. |
| `## Configuration` | How it is set up for this project, one `###` per environment. |
| `## Verification` | How to check its facts still hold. |

All six sections are always there; one that doesn't apply holds `None.`.

- **Who edits it:** you and the planner edit a resource by hand, inside a change
  or outside one as tiny work, and an implementer may edit one while building
  its item. A reviewer edits nothing. A resource never goes through deltas.
- **In a change:** a change that sets up or alters something outside the repo
  gets an item to create or update its resource and its `- Verified:` date.
- **For agents:** the explore context pack lists every resource. The implement
  and review packs carry each active resource that serves a spec the change has
  a delta for: its What it is and Access sections and the outline of the rest,
  which the agent reads with `wm show`. Retired resources are left out.

**Checks:** `missing-line`, `missing-section`, `unknown-kind`, `unknown-status`,
`invalid-date`, `unknown-spec` (a `- Serves:` name that isn't a spec).

## Records

Every line `wm` writes is a dated record. It names who it is by: your git name,
`wm-implementer` or `wm-reviewer` for an agent's ending, or the name given with
`--by`. A later record supersedes an earlier one; `wm resolve` adds a
`(resolved)` record and the blocker stays.

| Record | Where | Written by |
|---|---|---|
| `(accepted)` | Log | `wm accept`: the fingerprint and the items it covers |
| `(synced)` | Log | `wm sync`: the deltas merged before the archive |
| `(self-review)` | Log | `wm review --self`, with `covers <items>` and findings |
| `(review)` | Log | `wm verdict`, or the reviewer's ending: `pass`, `changes <items>` or `spec-gap`, then `covers <items>` |
| `(override)` | Log | `wm archive --override`: your reason for archiving past a missing review |
| `(blocked)` | item | `wm block`, or an implementer's `blocked` |
| `(gap)` | item | `wm gap`, or an implementer's `spec-gap` |
| `(note)` | item | `wm note`, or an implementer's `partial` |
| `(reopened)` | item | `wm reopen`: a review named it to rebuild |
| `(resolved)` | item or Log | `wm resolve`: what you decided |
| `(added)` | milestone Log | `wm roadmap add`: the change and its description |
| `(dropped)` | milestone Log | `wm roadmap drop`: the change and the reason |
| `(moved)` | milestone Log | `wm roadmap move`: the change, then `after <change>` or `first` |
| `(proposed)` | milestone Log | `wm new change --milestone`: the change |
| `(archived)` | milestone Log | `wm archive` of a member change: the change |

## What holds it together

- **`wm check`** reports every rule on this page, as errors and warnings, and
  runs in CI with `wm ci`. `wm check --fix` puts the active record in its
  standard layout and never changes wording.
- **The acceptance fingerprint** covers what you accepted: the proposal without
  its Outcome, the review level, the deltas, the design, each accepted item, and
  the living text the deltas touch. Layout fixes and comments don't count.
- **New work only.** The rules for the Impact, the decisions and the numbered
  charter lists hold for active changes, the charter and explorations. Archived
  changes are read as they were written.

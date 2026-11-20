# Changelog

All notable changes to Waymark, one entry per release.

## [Unreleased]

- **Skills ask less of you.** `wm-archive` shows the outcome it will write and
  runs `wm archive` itself once you say yes, instead of asking you to type the
  command. `wm-explore` and `wm-propose` label open questions Q1, Q2, options
  A, B and closing offers 1 to 4, so an answer can't be mistaken for a choice.
  `wm-propose` writes its own bold step names with the colon inside the bold,
  as `wm check` expects of labels.

## [0.5.0] - 2026-11-19

Explorations get a lifecycle, and the record one style: bold labels, records
that start with their date, and every record of a change in its Log.

- **Behavior change: `parked` is no longer an exploration status.** An
  exploration is `open`, `led-to <links>` or `dropped`, and `wm check` reports
  `parked` as an unknown status. An open exploration's Conclusion may say what it
  waits for. The record format is unchanged.
- **Behavior change: labels are bold.** Every label line in the record is
  written `- **<Label>:** <text>`, the colon inside the bold: a proposal's facts,
  Impact and Outcome, an item's lines, a decision's parts, a delta's `From`, `To`,
  `Reason` and `Repos`, an exploration's `Status` and a resource's four lines.
  The charter's glossary is `- **<term>:** <meaning>`. A label written plain, or
  with the colon outside, isn't read; `wm check` reports it as `plain-label`, and
  `wm check --fix` makes it bold.
- **Behavior change: every task item has a Build line**, `- **Build:** planner`
  or `- **Build:** delegate`, first among its lines. An item's lines come in the
  order Build, Repo, Criteria, Verify, before any record. `wm check` reports a
  missing Build line as `item-incomplete` and lines out of order as `item-order`;
  `wm check --fix` puts the lines in order.
- **Behavior change: a decision's options are a nested list**, one option per
  bullet, at least two. An `- **Options:**` line with text of its own is reported
  as `decision-options`; options are no longer split on `;` or "or".
- **Behavior change: records start with their date.** Every record, in a change
  and in a milestone's Log, is written `<date> (<kind>) [<args>] [by <who>]: <text>`.
  Item lists in records are separated by `, `, and a `changes` list that `covers`
  follows ends with `;`, as in `2026-11-20 (review) changes 1.2, 2.2; covers 1.1,
  1.2, 2.2 by wm-reviewer: <reasons>`. A record in the older shape is reported as
  `malformed-record`; no command migrates one.
- **Behavior change: a finding's severity is in brackets**, written
  ``- [critical] `<place>`: <text>``.
- **Behavior change: every record of a change goes in its `## Log`.** `wm block`,
  `wm gap`, `wm note`, `wm reopen`, `wm resolve <change> <item>` and an
  implementer's ending write their record into the Log, naming the item after
  the kind, as in `2026-11-20 (blocked) 1.2 by Ada: the API key is missing`, and
  write nothing under the item. `wm check` reports a record under an item in an
  active change as `misplaced-record`, and a record naming an item the change
  doesn't have as `unknown-item`. `wm show` and the implement context pack still
  show each item's records with the item. Each record in the `wm.show.change`
  JSON has an `item` field, and the Log in `wm show` names it.
- **Upgrading from 0.4.0.** The record format is unchanged, so `wm update`
  accepts a 0.4.0 record, and archived changes are read as they were written. A
  change still in flight keeps its old shapes, which `wm check` now reports:
  `wm check --fix` makes its labels bold and puts its item lines in order, and
  you add a `- **Build:** planner` line to each item and rewrite its records in
  the new shape, in its `## Log`. Or finish and archive the changes in flight
  before upgrading.
- **`wm new change --from <exploration>` and `wm new milestone --from
  <exploration>`** set the exploration's status to `led-to` the new change or
  milestone. A second `--from` adds its link after the first.
- **Explorations are archived with their work.** `wm archive` and `wm close`
  move an exploration to `explorations/archive/YYYY-MM-DD-<name>.md` once
  everything it led to is archived or closed, and re-aim the links to it.
- **`wm exploration drop <exploration> --reason "<why>"`** ends an open
  exploration that won't be acted on: it writes `dropped` and the reason, and
  moves it to the archive.
- **Agents can't edit an exploration's status line by hand.** The hooks refuse
  the edit and name `--from` and `wm exploration drop`.
- **Archived explorations in the views.** `wm show <exploration>` finds an
  archived one by its name or dated name and says when it was archived, and
  `wm ls explorations --archived` lists them. The explore context pack lists
  active explorations only. The `wm.show.exploration` JSON is at version 2, with
  an `archived_on` field, and `wm.context.explore` at version 2; both list
  `dropped` instead of `parked`.
- **`wm check` reports `exploration-not-archived`** for an active exploration
  whose work is all archived.
- **`wm init` and `wm update` write `explorations/archive/.gitkeep`.**
- **`/wm-explore <exploration>` picks a saved exploration back up:** it reads it,
  says what in the record has changed since, and goes on from its Questions and
  Approaches. Its closing offers for a saved exploration are do nothing, update or
  drop it, a proposal, or a milestone, the last two created with `--from`.
- **`wm show` prints records as they are written.** The Log and each item's
  records read `<date> (<kind>) …`, with item lists separated by commas, and
  findings read ``[<severity>] `<place>`: <text>``. A review written without
  `covers` adds a line saying it covers every item. Each record in the
  `wm.show.change` JSON has a `line` field holding it as written.
- **The context packs use the record's own shapes.** An item's labels are bold,
  `- **Criteria:**`, and earlier findings are in brackets, so what an agent
  copies from a pack is what `wm check` expects.

Smoke test: passed on 2026-11-19 with Claude Code 2.1.328 on Windows.

## [0.4.0] - 2026-11-18

A first impression worth the name: `wm init` welcomes you and asks what to set
up, and every terminal view has one palette, tree lines and wrapped prose.
Review findings name their places relative to the project. The record format is
unchanged.

- **Behavior change: `wm init` asks on a terminal.** With both its input and its
  output a terminal, and none of `--atlas`, `--tool` or the new `--yes`, it opens
  with a welcome screen: the Waymark star, which grows in and twinkles, the
  tagline, what it sets up, and the skills to run next. It then asks whether the
  repository is a project or an atlas (and the atlas's name), which agent tools
  to set up, with the ones it finds already selected, and whether to add the CI
  workflow. Esc or Ctrl+C cancels and writes nothing. Where the terminal can't
  read single keys, the questions come as numbered choices. In a clone, it shows
  the welcome screen and asks nothing.
- **Behavior change: `wm check` groups its findings by file.** Each file's path
  is on a line of its own, with its findings under it as
  `  <severity>: <line>: <code>: <message>`, instead of one
  `<severity>: <path>:<line>: <code>: <message>` line per finding. A script that
  reads the text output should read `wm check --json`, which is unchanged.
- **`wm init --yes`** asks nothing. So do `--atlas` and `--tool`, and so does
  `wm init` when its input or output isn't a terminal, as when an agent runs it:
  it does what it did before.
- **A new look in the terminal.** The views use one palette of the 16 standard
  colors, by role: cyan for section rules and commands, green for done, yellow for
  what needs you and for warnings, red for errors, dim for dates and records, bold
  for names. `wm status` colors each change's phase and progress bar and marks each
  milestone's roadmap lines `◆` archived and `◇` open. `wm show` draws a change's
  items as a tree and marks a milestone's roadmap. `wm doctor` lines its checks up
  in one column. Each glyph has an ASCII stand-in for consoles that can't show it.
- **Prose wraps on a terminal.** `wm show`, `wm inbox`, `wm check` and
  `wm doctor` wrap their prose to the terminal's width, from 60 to 100 columns.
  Output that isn't going to a terminal is not wrapped, so agents read whole lines.
- **`FORCE_COLOR`.** Set to any value but empty or `0`, it turns color on when the
  output isn't a terminal. `NO_COLOR` still turns color off, and wins. JSON output
  never carries color.
- **Finding places are relative to the project.** `wm review` and `wm verdict`
  write an absolute path in a finding's place relative to the project, with
  forward slashes, or as `<repo>/<path>` for a code repo in an atlas, and refuse
  any other absolute path. Before, a reviewer's absolute path went into the
  record as given, home folder included.

Smoke test: passed on 2026-11-18 with Claude Code 2.1.327 on Windows.

## [0.3.0] - 2026-11-18

Context beyond the code: resources, a spec's Background and one list of project
rules give every fact an agent needs one place. Milestones link their changes and
keep a log, changes have branches and bases, and the record format resets to 1.

- **Behavior change: record format 1, with no migration.** `wm` reads and writes
  only format 1, and this release's record is format 1. A record in any other
  format, including the format 3 that 0.2.0 writes, is refused with one reason:
  install the `wm` version that wrote it. `wm update` migrates nothing. It
  regenerates the files `wm` owns and adds missing `.gitkeep` files. `wm check`
  no longer reports older layouts on their own; such a line fails the check
  that applies to it. `.waymark/atlas.toml` is no longer read as an atlas
  pointer, and `wm doctor` no longer looks for `.waymark/hooks/`.
- **Behavior change: `wm-fix` is gone; `/wm-propose` does work of any size.**
  It reads the specs and the code and picks the path itself: tiny, built after
  your yes; short, a change with no design; or full, a change with a design,
  with any open question blocking acceptance. `wm init` and `wm update` remove
  the `wm-*` skill folders `wm` no longer ships, and print `removed:` for each.
- **Record folders stay in git.** `wm init` writes an empty `.gitkeep` into
  `specs/`, `changes/`, `changes/archive/`, `explorations/`, `milestones/` and
  `milestones/archive/`, and `wm update` adds any that are missing.
- **Behavior change: an item added after a review is reviewed on its own.**
  `(review)` and `(self-review)` records now name the items they cover, as
  `covers <item>...`; a record without it covers every item. Once an item added
  after a passing review is ticked, the next step is a review of the items no
  passing review covers, and the reviewer's pack holds only those. `wm archive`
  refuses a change with such an item unless you override it with a reason.
  `wm show` and the JSON payloads give what each review covers.
- **A change names its milestone.** A proposal may have a `- Milestone: <name>`
  line. For an active change, `wm check` reports an error when that line and the
  milestones' roadmaps disagree, including a roadmap that links a change whose
  proposal has no such line. `wm new change <name> --milestone <milestone>`
  writes the line and links the change from the roadmap. The implement and
  review context packs carry the milestone's Goal and Non-goals, in a new
  `milestone` field.
- **A milestone keeps a log, and its roadmap changes only through `wm`.**
  `wm roadmap add`, `wm roadmap drop --reason` and `wm roadmap move --after|--first`
  change the roadmap, and each writes a record in a `## Log` at the end of
  `milestone.md`, as do `wm new change --milestone` and `wm archive`. An agent's
  hand edit to a roadmap line or the Log is refused.
- **Behavior change: `wm close` needs every roadmap line archived.** A planned
  line that was never proposed now keeps a milestone open, until it is proposed
  or dropped with `wm roadmap drop`.
- **Each change has a branch and a base.** A proposal may say which change it
  comes after, in an `- After: <change>` line written by
  `wm new change <name> --after <change>`. `wm instructions`, `wm pr` and
  `wm status` show each change's branch and base, `wm pr`'s JSON has a `base` for
  the pull request to target, and `wm check` warns when the change it comes after
  has merged. The default branch comes from the `origin` remote's HEAD, or is
  `main`. The skills open a plan pull request for a new milestone and create
  each change's branch from its base.
- **Resources.** A new kind of note, `waymark/resources/<name>.md`, holds the
  facts about one thing outside the repo: its kind, the specs it serves, its
  status, the day it was verified, and six sections. `wm new resource <name>
  <kind>`, `wm ls resources` and `wm show <name> --kind resource` work with them,
  and `wm check` holds them to their layout. The explore context pack gains a
  `resources` index, and the implement and review packs a `resources` field with
  the resources serving the change's specs. An implementer may edit resources,
  and `wm init` and `wm update` keep `resources/` in git.
- **A spec may have a Background.** A `## Background` section, between Purpose
  and Requirements, holds the facts about the spec's area that aren't
  requirements. A delta's `## Background` replaces the spec's whole at archive or
  sync. `wm check` reports an empty one. The implement and review packs gain a
  `backgrounds` field with the Background of each spec the change has a delta
  for, the delta's when it has one. The delta template and the specs step's
  guidance say where a fact goes.
- **Behavior change: the charter's Rules are one numbered list.** `## Rules`
  holds `1. <rule>` lines, like Goals and Constraints, and every agent gets the
  whole list at every step: `wm instructions` and every `wm context` pack show
  it under "Project rules", and `rules` in their JSON holds all of it. A step
  heading or a bullet under Rules is a `numbered-list-format` error, and the
  `unknown-step` problem is gone. A charter with step headings must be rewritten
  by hand. `wm init` writes Rules without step headings.

Smoke test: passed on 2026-11-18 with Claude Code 2.1.327 on Windows.

## [0.2.0] - 2026-11-16

The planner builds by default and each change is reviewed once. Small work takes
a tiny path. The record moves to format 3, with structured notes, step
checklists and one layout for every skill.

- **Behavior change: the planner builds the items.** At the apply step,
  `wm instructions` tells the session to build the item from its context pack,
  run the checks the item touches, and record the result with `wm tick`,
  `wm block` or `wm gap`. An item with a `- Build: delegate` line still goes to a
  fresh implementer. In an atlas, the planner may edit any code repo; an
  implementer edits only its item's repo.
- **Behavior change: one review per change.** A change's review level comes from
  a `- Review:` line in its proposal, or from `default_review`; items no longer
  carry one. Once every item is ticked, the whole change is reviewed once, with
  `wm review <change> --self "<summary>"` or by the `wm-reviewer` agent started
  with the change's name. A `changes` verdict names the items to rebuild, and
  `wm reopen` reopens each one. A pass with a critical finding is refused.
- **The tiny path.** Work that adds, changes or removes no requirement needs no
  change. The new `wm-fix` skill builds it after your yes, commits it, and offers
  a pull request. `wm-propose` asks first which path fits.
- **Archive before the pull request.** A change is archived on its own branch, so
  the code, the merged specs and the archived change go in one pull request.
  `wm pr` describes an archived change, with its outcome.
- **Adding an item keeps acceptance.** The `(accepted)` record names the items it
  covers. Changing or removing an accepted item, the proposal, a delta or the
  design still withdraws it.
- **Behavior change: no `.waymark/` folder and no git hooks.** `wm git-hooks` and
  `wm run-hook` are removed. In Claude Code, the command hook refuses a
  `git commit` whose message isn't a conventional commit with an allowed scope;
  commits made outside an agent aren't checked. A code repo points at its atlas
  through a pointer-only `waymark/config.toml`, written by `wm atlas point`.
  `.waymark/atlas.toml` is still read, with a warning.
- **Upgrading from 0.1.x.** This version can't migrate a record made by 0.1.x,
  which is format 1: `wm update` refuses it and changes nothing (see record
  format 3 below). In each clone that 0.1.0 or 0.1.1 set up, run
  `git config --unset core.hooksPath` and delete the hooks folder it named, as
  [Upgrading](docs/getting-started.md#upgrading) describes.
- **A new README and two new references.** The README opens with a diagram of
  a change's trail and works as an index: the three paths and the steps, a
  quick start with a setup matrix, the skills, and a real walk-through of adding
  dark mode with the files it writes. [The record](docs/record.md) covers every
  file and [Skills and agents](docs/skills.md) every skill and agent.
- **One severity rubric for every review.** `wm context --for review` and
  `wm instructions` at the review step give it, as "Severity rubric" and, in the
  JSON, `severity_rubric`: critical when a criterion or scenario doesn't hold,
  warning when everything holds but something is fragile, suggestion for
  clarity, and the higher of two when torn. The reviewer and the self-review in
  `wm-apply` grade by it.
- **Stopping rules for the implementer.** `wm context --for implement` gives
  them, as "When to stop" and, in the JSON, `stopping_rules`: `spec-gap`,
  `blocked`, or `partial` after three attempts at the same failing check.
- **The skills share one layout:** Role, Inputs, Steps, any sections of their
  own, Quality bar, Show the human, When to stop and Rules. Each says what good
  output looks like, the fixed shape of what it shows you, and when it stops.
  - `wm-propose` asks what the record doesn't settle before drafting, and checks
    the proposal, deltas, design and tasks against each other before acceptance.
  - `wm-kickoff` interviews you one charter section at a time.
  - `wm-explore` states what the record says, the questions, two or more
    approaches with their costs, and a recommendation.
- **`wm instructions` gives the specs step rules for writing requirements,** and
  the tasks step rules for sizing items, in its guidance.
- **`wm instructions` gives each drafting step a checklist** (propose, specs,
  design, tasks): what must hold before moving on, each check marked when
  `wm check` enforces it. The JSON gains `checklist`, a list of `text` and
  `enforced`.
- **`wm instructions` gives every step the shared rules** that every skill
  follows, as "Shared rules" and, in the JSON, `shared_rules`. The skills no
  longer repeat them.
- **Behavior change: two new checks for active changes.** A task item needs a
  `- Criteria:` and a `- Verify:` line (`item-incomplete`), and a design
  decision needs at least two options under `- Options:` (`decision-options`),
  as bullets or on the line joined by "or" or ";".
- **Behavior change: a milestone is one `milestone.md`,** with `## Goal`,
  `## Done when`, `## Non-goals` and `## Roadmap` in that order, instead of
  `goal.md` and `roadmap.md`. `wm new milestone` writes it, only the list lines
  under `## Roadmap` count as the milestone's changes, and archiving a change
  ticks its line there. `wm check` reports a `goal.md` or `roadmap.md` in a
  milestone folder, active or archived; merge the two files into `milestone.md`
  by hand, goal first, then the roadmap's lines under `## Roadmap`.
- **Behavior change: `wm archive --built` and `--differs` replace `--outcome`.**
  The archived proposal's Outcome holds a `- Built: <text>` line and a
  `- Differs: <text>` line, `none` when `--differs` is left out. A hand-written
  Outcome needs both lines. `wm pr` shows them.
- **Behavior change: a proposal's Impact has three lines,** `- Specs:`,
  `- User-visible:` and `- Code:`. `Specs:` names each spec the change has a
  delta for, in backticks, or says `none`, and `wm check` reports a spec named
  without a delta and a delta whose spec isn't named. `- Specs: none` replaces
  "No spec changes" as the way to say a change has no deltas.
- **Behavior change: a design's decisions are settled before acceptance.** Each
  decision has a `- Status: proposed|decided` line and a
  `- Decided by: human|planner` line, and the design an `## Open questions`
  section, holding a list or `None.`. While a decision is proposed or a question
  is listed, the next step stays at the design, and `wm accept` refuses with a
  reason that names each one.
- **The charter's goals and constraints are numbered lists,** `1. <text>`,
  counted from 1. `wm check` reports a line in another form.
- **A task item's `- Verify:` may be a nested list,** one step per bullet, like
  `- Criteria:`.
- **An exploration's status comes from its `- Status:` line alone.** A
  Conclusion starting with `Parked:` no longer parks it, and a missing status
  line is reported as `missing-status` instead of an old layout.
- **The templates carry a good and a bad example** in a comment. Comments are
  left out of the acceptance fingerprint, so editing or deleting them keeps an
  acceptance.
- These layouts are required of active changes, the charter and explorations.
  Archived changes are read as they were written, and the record format stays
  3.
- **Behavior change: record format 3.** `wm` reads and writes only format 3. It
  doesn't migrate a record in format 1 or 2: `wm update` refuses one, names its
  format, and changes nothing. Waymark's own record was the only one in an older
  format, and was moved by a migration that has since been removed.
- **The layouts humans write:**
  - a proposal's facts are bullets: `- Owner: <name>`, `- Review: <level>`,
    `- Path: short`;
  - the charter's glossary is a list of `- **<term>**: <meaning>`, and step
    headings under Rules are capitalized (`### Apply`) and may be left out;
  - a task item's criteria may be a nested list under `- Criteria:`, and the
    delegation tag is a `- Build: delegate` line under the item;
  - a delta's sections are `## ADDED Requirements`, `## MODIFIED Requirements`
    and `## REMOVED Requirements`, and `## RENAMED Requirements` with `- From:`
    and `- To:` renames a requirement and keeps its text;
  - an exploration says where it stands in a `- Status: open|parked|led-to
    <link>` line under its title.

  `wm check` reports each older layout and says to run `wm update`.
- **Behavior change: what `wm` writes is a dated record,**
  `(kind) YYYY-MM-DD [<args>] [by <who>]: <text>`. `(blocked)`, `(gap)`,
  `(note)`, `(reopened)` and `(resolved)` sit under items; `(accepted)`,
  `(synced)`, `(self-review)`, `(review)`, `(resolved)` and `(override)` sit in a
  `## Log` section at the end of the task list, which replaces `## Review`. The
  proposal no longer holds `Accepted:` or `Synced:` lines.
- **Records are never removed.** `wm resolve` adds a `(resolved)` record and
  keeps the blocker or spec gap it resolves. Accepting again adds a new
  `(accepted)` record; the latest counts.
- **Every writing command takes `--by`**; records name your git name by default,
  and `wm-implementer` or `wm-reviewer` for an agent's result.
- **`wm note <change> <item> "<text>"`** writes a note. An implementer no longer
  edits the task list; `wm note` is the one writing command it may run.
- **`wm check --fix`** puts the active record in its standard layout and never
  changes wording. The acceptance fingerprint is taken over that layout, so a
  fix never withdraws an acceptance.
- **Findings** put their place in backticks: ``warning `src/a.py:12`: <text>``.
- **`wm show --json`**: the `show.change` schema is version 3, with a `log` of
  records, a `by` on every record, and no item `notes` or review `records`.

Smoke test: passed on 2026-11-16 with Claude Code 2.1.326 on Windows.

## [0.1.1] - 2026-11-15

Each machine sets itself up, and background agents' results are recorded.
Waymark is now developed with its own record.

- **Behavior change: the agent tool files and git hooks belong to each
  machine.** `wm init`, `wm update` and `wm git-hooks` keep them out of git with
  a marked block in `.gitignore`, and the git hooks are no longer staged. Commit
  `waymark/` and `.gitignore`; after cloning, run `wm init`.
- **`wm init` in a clone that has a record** sets up this machine instead of
  refusing, and leaves the record alone. It needs the pinned `wm`, and says to
  run `wm update` when the record needs migrating.
- **`wm doctor`** warns when files `wm` writes for a machine are tracked in git,
  with the `git rm -r --cached` command that stops sharing them. Its message for
  missing agent files says to run `wm init`.
- **`wm update`** asks you to commit only when the record, `.gitignore` or the
  CI workflow changed.
- **Fix: results from agents run in the background are recorded.** In Claude
  Code, an implementer's or reviewer's report handed back through
  `SubagentHandback` is read by the hooks, so ticks and verdicts are written
  without the planner. The agents may now use that tool.
- **Upgrading from 0.1.0:** change the pin to 0.1.1, install it, and run
  `wm update`. It adds the `.gitignore` block. Then run `wm doctor` and the
  `git rm -r --cached` command it gives, and commit. The record format is
  unchanged (format 1); nothing is migrated.

Smoke test: passed on 2026-11-15 with Claude Code 2.1.325 on Windows.

## [0.1.0] - 2026-11-13

The first release: the foundation.

- **The record:** charter, settings, living specs, changes (proposal, deltas,
  design, tasks), milestones, explorations and a dated archive, all plain
  markdown in `waymark/`. Record format 1.
- **The workflow:** propose, specs, design, tasks, accept, apply, review and
  archive, with a short path for small changes. Acceptance is fingerprinted, and
  editing an accepted change withdraws it.
- **Review:** levels `self`, `independent` and `none`; evidence written only by
  `wm`; the accept, delegation and archive gates; `wm archive --override` for a
  missing review, with the reason recorded.
- **Commands:** setup (`init`, `update`, `doctor`), authoring (`new`), the agent
  interface (`instructions`, `context`), the lifecycle commands, and the views
  (`status`, `inbox`, `show`, `ls`, `check`), with `--json` and versioned
  schemas. Styled output with an ASCII fallback.
- **Claude Code:** eight skills, the implementer and reviewer agents, and hooks
  that enforce the agent-side rules and record results from agents' final lines.
- **Teams:** change owners, branch-safe merges, overlaps reported by `wm check`
  and mismatches blocked at archive.
- **Multi-repo:** atlases, a per-machine registry, pointer files in code repos,
  read-only references to other atlases, edit limits across repositories, and
  `wm atlas doctor`.
- **Git and CI:** committed git hooks (commit-message check, and `wm check` on
  commits that touch the record), a GitHub Actions workflow (`wm ci`), and pull
  request text from a change (`wm pr`).
- Runs on Windows, macOS and Linux, on Python 3.11 and newer, with no
  dependencies beyond the standard library.

Smoke test: passed on 2026-11-13 with Claude Code 2.1.325 on Windows.

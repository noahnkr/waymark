# Changelog

All notable changes to Waymark, one entry per release. A release that changes
the record's format says whether `wm update` migrates an older record.

## [Unreleased]

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

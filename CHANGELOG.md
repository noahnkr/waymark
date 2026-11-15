# Changelog

All notable changes to Waymark, one entry per release. A release that changes
the record's format says what `wm update` migrates.

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

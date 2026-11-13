# Changelog

All notable changes to Waymark, one entry per release. A release that changes
the record's format says what `wm update` migrates.

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

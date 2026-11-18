# Tasks

## 1. Dependencies, branches and bases

- [x] 1.1 Read and write the `- After:` line, and check it
  - Criteria:
    - `Proposal.after` holds the value of an `- After:` bullet, and is None without one
    - `wm new change <name> --after <change>` writes `- After: <change>` after `- Milestone:`, refuses an invalid name, and `--after` is refused for a milestone or an exploration
    - `wm check` reports `unknown-after`, `after-self` and `after-cycle` as errors on an active change's proposal, each naming the change or the cycle
  - Verify: tests in `tests/record/`, `tests/services/test_setup.py`, `tests/services/test_check.py` and `tests/test_cli.py` for the scenarios "Change written after another", "Unknown change named", "Cycle", "New change" and "Fact without a bullet"
- [x] 1.2 Work out each change's branch and base, and warn about a merged base
  - Criteria:
    - `git.default_branch` gives the `origin` remote's HEAD without its prefix, or `main`; `git.is_merged` tells whether a branch, local or on `origin`, is in the default branch, and is false for a branch that exists nowhere
    - `record/branches.py` gives each active change its branch, its base and whether the change it comes after is merged, asking git once for the default branch and once per stacked change
    - `wm check` warns `after-merged` when the change it comes after is archived or its branch is merged, naming the rebase, the pull request and the `- After:` line
  - Verify: tests in `tests/record/` and `tests/services/test_check.py` with real git repositories, for the scenario "Dependency merged" and for a remote's HEAD, no remote, and a branch merged only on `origin`
- [x] 1.3 Show the branch and base in `wm instructions`, `wm pr` and `wm status`
  - Criteria:
    - `wm instructions` gives `branch` and `base` for a change in its JSON and says them in its text
    - `wm pr` gives `base` beside `branch` in its JSON, and its text names the pull request from the branch into the base
    - `wm status` gives `branch` and `base` for each change in its JSON, and prints `on <base>` under a change whose base isn't the default branch
    - the payload schemas declare the fields, and `docs/cli.md` and `docs/json.md` are regenerated
  - Verify: tests in `tests/services/test_agent_interface.py`, `tests/services/test_ci_and_pr.py` and `tests/views/` for the scenarios "Change without a dependency", "Stacked change", "Pull request of a stacked change", "Status of a stacked change" and "Dependency merged"

- [x] 1.4 Count a dependency as merged when the default branch holds its archive
  - Criteria:
    - `git.archived_on` lists the folder names under the record's `changes/archive/` in `origin/<default>`, or in the local default branch without a remote, without checking anything out, and is empty when the branch or the folder exists nowhere
    - `record/branches.py` counts the change a change comes after as merged when it is archived in the record or the default branch holds a `<date>-<change>` folder for it, reading the archived names once per command; `git.is_merged` and its ancestor check are gone
    - a dependency branch just created from the default branch, with no commits of its own, is not merged, and the stacked change's base is that branch
    - a dependency merged by a squash or a rebase, whose archive is on the default branch, is merged, with no `after-merged` warning missed
  - Verify: tests in `tests/record/test_branches.py` and `tests/services/test_check.py` with real git repositories, for the scenarios "Stacked change" and "Dependency merged", a dependency branch with no commits, and a dependency squash-merged on `origin`

## 2. Skills and docs

- [x] 2.1 Keep one branch shape in the skills, and describe it in the docs
  - Criteria:
    - `wm-explore` puts a new milestone on a `plan-<milestone>` branch and offers a plan pull request before any member change is proposed
    - `wm-propose` creates a change's branch from its base before `wm new change`, and passes `--after` for a change that needs an unmerged one
    - `wm-apply` works on the branch `wm instructions` gives, and `wm-pr` opens the pull request into the `base` of `wm pr`, without asking which branch
    - in an atlas, the skills use the same branch name in every repo a change touches
    - `docs/concepts.md` and `docs/record.md` describe `- After:`, a change's branch and base, the merged-base warning and the plan pull request; the changelog's Unreleased section has the line
    - the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync pytest tests/adapters tests/test_docs.py`, codespell and `wm check`, for the scenarios "Milestone plan pull request", "Branch before the change" and "Pull request into the base"

## Log

- (accepted) 2026-11-17 fingerprint 7293ac9130dea93b items 1.1 1.2 1.3 2.1 by Noah Roberts
- (review) 2026-11-17 pass covers 1.1 1.2 1.3 2.1 by wm-reviewer: every item's criteria and every delta scenario hold, and tests, lint, format, types, spelling, docs freshness and wm check are all clean; the two warnings are untested or unlisted edges of the git merge check
  - warning `src/waymark/record/git.py:321 is_merged`: a dependency branch with no commits beyond the default branch is an ancestor of it and counts as merged, so a just-created dependency gives the stacked change the default branch as its base and a false after-merged warning; untested (tests/record/test_branches.py commits on add-limit first)
  - warning `src/waymark/record/branches.py:70 _is_merged`: a dependency merged by squash or rebase is never seen as merged (not an ancestor, and its archive isn't in the stacked branch's record until rebased), so after-merged never fires and the base keeps naming the dependency; not listed in the design's risks
- (accepted) 2026-11-17 fingerprint e9b81e1626baa357 items 1.1 1.2 1.3 1.4 2.1 by Noah Roberts
- (review) 2026-11-17 pass covers 1.4 by wm-reviewer: every criterion of 1.4 holds (archived_on reads origin or the local branch without a checkout, Branches counts a dependency as merged from the record or the default branch's archive, the ancestor check is gone, a branch with no commits isn't merged, a squash merge is merged and after-merged follows it), the earlier review's two warnings are fixed, and the 1218 tests, lint, format, types and wm check are clean; the warnings are missing check-level tests, archived-name reuse and the untested local-branch fallback
  - warning `tests/services/test_check.py`: item 1.4's verification asks for real-git tests of after-merged here (squash-merged dependency on origin, dependency branch with no commits, "Stacked change", "Dependency merged"), but none were added; the existing after-merged tests run without git, so "no after-merged warning missed" is covered only through Branches in tests/record/test_branches.py
  - warning `src/waymark/record/branches.py:70 _is_merged`: a change name can be reused after archiving (services/setup.py:155 refuses only active names), so an old `<date>-<name>` folder on the default branch marks a new active dependency of that name as merged, giving the stacked change the default branch as its base and a false after-merged warning; untested and not in the design's risks
  - warning `tests/record/test_branches.py:63`: git.archived_on is only tested with an origin remote; the criterion's fallback to the local default branch when there is no remote is never exercised
- (accepted) 2026-11-17 fingerprint 68ce0b48ab289ce6 items 1.1 1.2 1.3 1.4 1.5 2.1 by Noah Roberts
- (accepted) 2026-11-17 fingerprint ad94015e43800b1f items 1.1 1.2 1.3 1.4 2.1 by Noah Roberts

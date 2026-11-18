# Add change dependencies: design

## Context

- `record/proposal.py` reads the facts `Owner`, `Milestone`, `Path` and `Review` with `parse_facts`; any other bullet above the first section is prose.
- `record/git.py` runs git through `_run` and has `current_branch`, `head_commit` and `remote_url`, but nothing for a remote's HEAD or whether one branch is merged into another.
- `views/payloads.status` builds each change's summary with `_change_summary`, and in an atlas `_Branches` adds each repo's checked-out branch; `views/render._change_line` and `_branch_lines` print them.
- `services/instructions.py` builds the instructions payload, with `change` and `step` at its top; `services/pr.describe` builds the pull request with `branch` set to the change's name; `views/render.pr` prints the head line "from <branch>".
- `services/check.py` holds the record-wide findings, such as `_milestone_findings`.
- `services/setup.create_change` writes the facts from `--owner`, `--milestone` and `--short`.
- The skills `wm-explore`, `wm-propose`, `wm-apply` and `wm-pr` describe branches only as "the change's branch", and `wm-pr` asks the human for the target.

## Approach

1. **The fact.** `parse_proposal` also reads `AFTER = "After"`, and `Proposal` gains `after: str | None` and `after_line`. `create_change` takes `after`, refuses a name that isn't a valid change name, and writes `- After: <change>` after `- Milestone:`. `cli.py` adds `--after <change>` to `wm new change`, refused for a milestone or an exploration.
2. **Git.** `record/git.py` gains `default_branch(repository)`, the short name of `refs/remotes/origin/HEAD` without its `origin/` prefix, or `main`; and `archived_on(repository, into, folder)`, the names of the folders under a path in `origin/<into>`, or in `<into>` without a remote, read with `git ls-tree` and without checking anything out; empty when the branch or the path exists nowhere.
3. **Branches.** A new `record/branches.py` holds `Branches(record)`, which reads the default branch and the names archived on it once, with `of(change) -> ChangeBranch(branch, base, after, merged)`. `merged` is true when the change it comes after is archived in the record, or the default branch holds a `changes/archive/<date>-<change>` folder for it that this record doesn't hold; an archived folder this record already holds came from an earlier change of the same name, so it doesn't count. The base is then the default branch, and otherwise the after change's name. The record's folder is found relative to the repository's top. In an atlas, git is asked in the atlas's own repository.
4. **Checks.** `services/check.py` gains `_branch_findings`: errors `unknown-after` (no active or archived change has the name), `after-self`, and `after-cycle` (following `- After:` lines among active changes returns to the change, reported on each change in the cycle); and the warning `after-merged`, which names the rebase onto the default branch, the pull request and the `- After:` line.
5. **Views.** `wm instructions` adds `branch` and `base` to its JSON for a change, and its text says "Branch <branch>, based on <base>." `wm pr` adds `base` to its JSON beside `branch`, and its head line reads "from <branch> into <base>"; the description itself is unchanged. `wm status` adds `branch` and `base` to each change in its JSON, and its text prints `on <base>` under a change whose base isn't the default branch. The payloads keep their versions: the fields are new.
6. **Skills.** `wm-explore` starts a milestone on a `plan-<milestone>` branch from the default branch, commits it, and offers a plan pull request before any member change is proposed. `wm-propose` reads the base `wm` will give (the default branch, or the unmerged change it comes after), creates the branch `<name>` from it, then runs `wm new change <name>`, with `--after <change>` when it needs an unmerged change. `wm-apply` checks it is on the branch `wm instructions` gives. `wm-pr` opens the pull request into the `base` of `wm pr --json`, not asking the human which branch. In an atlas, each skill uses the same branch name in every repo the change touches.
7. **Docs.** `docs/concepts.md` and `docs/record.md` describe `- After:`, branches and bases, and the plan pull request; `docs/cli.md` and `docs/json.md` are regenerated; the changelog gets its line.

## Decisions

### Decision: How a change names what it comes after
- Status: decided
- Decided by: human
- Options: one `- After: <change>` line; a list of changes
- Choice: one change, in an `- After:` line, written by `wm new change --after`
- Why: a branch has one base, which matches how a stacked pull request works

### Decision: Where the default branch comes from
- Status: decided
- Decided by: human
- Options: the `origin` remote's HEAD, falling back to `main`; a `base_branch` setting in `config.toml`
- Choice: the remote's HEAD, or `main`
- Why: nothing to configure, and it follows the repository

### Decision: When a base counts as merged
- Status: decided
- Decided by: human
- Options: the change it comes after is archived in the record, or git finds its branch in the default branch; archived in the record only; archived in the record, or the default branch holds its archived folder
- Choice: archived in the record, or the default branch holds its archived folder
- Why: a change is archived on its own branch before its pull request, so its archived folder is on the default branch exactly when it has merged, whether by a merge commit, a squash or a rebase; asking whether its branch is an ancestor of the default branch counted a just-created dependency branch, with no commits of its own, as merged, and missed squash and rebase merges. This was revised after the independent review found both

### Decision: How `wm status` shows a base
- Status: decided
- Decided by: human
- Options: an `on <base>` line under a change whose base isn't the default branch; a branch line under every change
- Choice: the line only for a change not based on the default branch, with branch and base always in the JSON
- Why: ordinary changes stay one line, and a stacked one stands out

### Decision: Showing the checked-out branch in a single repository
- Status: decided
- Decided by: planner
- Options: warn when a change's branch isn't checked out; say nothing
- Choice: say nothing
- Why: in one repository only one branch is checked out at a time, so every other change would warn; an atlas already reports its repos' branches

### Decision: Where branches are worked out
- Status: decided
- Decided by: planner
- Options: in `record/state.py`, with the change states; in a new `record/branches.py`, used by the views and the check
- Choice: a new `record/branches.py`
- Why: it calls git, which `derive_state` doesn't, and caching the git calls once per command keeps the views fast

### Decision: Errors and the warning
- Status: decided
- Decided by: planner
- Options: errors for an unknown change, the change itself and a cycle, with a warning for a merged base; every case a warning
- Choice: errors for the three that make the base unknowable, a warning for a merged base
- Why: an unknown or circular `- After:` leaves no base to give, while a merged base still has one, the default branch, and only asks the human to tidy up

## Open questions

None.

## Risks and trade-offs

- `wm status`, `wm instructions`, `wm pr` and `wm check` now call git, once for the default branch and once for the changes archived on it, and only when a change has an `- After:` line; without git, or outside a repository, the default branch is `main` and nothing counts as merged by git.
- A dependency merged on the remote but not fetched isn't seen as merged until the next fetch.
- A dependency merged without being archived first, against the skills, isn't seen as merged; the base keeps naming its branch until the change is archived or its `- After:` line is taken off.
- The skills create and switch branches through git themselves; `wm` only names them.

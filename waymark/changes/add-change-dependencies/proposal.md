# Add change dependencies

- Owner: Noah Roberts
- Milestone: stronger-milestones
- Review: independent

## Why

`wm` assumes every change's branch is named after it, but not what that branch is based on. When one change needs another that isn't merged yet, the planner stacks it on the other's branch by hand, nothing records that, and its pull request is opened against whatever branch the human remembers. Once the first change merges, the stacked branch keeps pointing at a branch that's gone. The milestone's branches should follow one shape: the milestone lands on `main` in a plan pull request, and each change branches from `main`, or stacks on the unmerged change it comes after, and merges into `main` on its own.

This is the last change of `stronger-milestones`.

## What changes

- **A change may say what it comes after.** An optional `- After: <change>` fact names one other change. `wm new change <name> --after <change>` writes it. `wm check` reports an `- After:` that names no known change, the change itself, or that forms a cycle.
- **Each change has a branch and a base.** Its branch is its name. Its base is the branch of the change it comes after, while that change is unmerged, and otherwise the default branch: the remote's HEAD, or `main` without a remote.
- **The views show them.** `wm instructions` and `wm pr` carry the branch and the base in their JSON and text; `wm pr`'s pull request targets the base. `wm status` adds an `on <base>` line under a change whose base isn't the default branch, and its JSON always carries both.
- **A merged base is reported.** `wm check` warns when the change a change comes after is archived, or its branch is already in the default branch, and says to rebase onto the default branch, retarget the pull request and take the `- After:` line off.
- **The skills follow the shape.** `wm-explore` opens a plan pull request for a new milestone; `wm-propose` creates a change's branch from its base before `wm new change`; `wm-apply` and `wm-pr` use the branch and base `wm` gives; in an atlas, every code repo uses the same branch names.

## Non-goals

- `wm` creating, switching, rebasing or pushing branches, or opening pull requests.
- A change depending on more than one other change.
- A long-lived milestone branch.
- Configuring the default branch.
- Showing a branch that doesn't match a change in a single repository; an atlas already warns.

## Impact

- Specs: `branches` (new: the `- After:` line and its checks, a change's branch and base, the views, the merged-base warning); `authored-formats` (the proposal facts gain `- After:`); `skills` (branches in the skills).
- User-visible:
  - a proposal may have an `- After: <change>` line, written by `wm new change --after`;
  - `wm instructions`, `wm pr` and `wm status` show each change's branch and base, and `wm pr`'s JSON has a `base` to target;
  - `wm check` reports a bad `- After:` and warns about a change based on a merged branch;
  - the skills open a plan pull request for a new milestone and create a change's branch from its base.
- Code: the proposal facts (`record/proposal.py`), the default branch and merge checks (`record/git.py`), branches and bases (`record/state.py` or a new `record/branches.py`), the checks (`services/check.py`), `wm new change` (`cli.py`, `services/setup.py`), `wm instructions` (`services/instructions.py`), `wm pr` (`services/pr.py`), the views (`views/`), the `wm-explore`, `wm-propose`, `wm-apply` and `wm-pr` skills, and the docs.

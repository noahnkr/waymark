# Stronger milestones

## Goal

Make a milestone, when the human chooses one, a part of the workflow rather than a list of links: it steers the changes that work toward it, and it stays honest while the work is still being discovered. Every member change knows its milestone, and its agents get the milestone's goal and non-goals. The roadmap always shows the plan as it stands, changed only through `wm`, and the milestone's log records how it got there: what was added, dropped, moved, proposed and archived. Branches follow one shape: the milestone and its drafted proposals land on `main` in a plan pull request; each change branches from `main`, or stacks on the unmerged change it comes after, and merges into `main` on its own, so `main` sees the milestone's work as it lands and nothing drifts. `wm` says which branch and base each change has; the skills create and switch the branches.

## Done when

- A change's proposal may name its milestone in a `- Milestone:` line; `wm check` reports a proposal and a roadmap that disagree, and `wm new change <name> --milestone <milestone>` adds the change to the roadmap.
- The implement and review packs of a member change carry its milestone's Goal and Non-goals.
- The roadmap is changed with `wm` commands that add, drop (with a reason) and move a line; hand edits to roadmap lines are refused; each command, a change's proposal and its archive write a dated record in the milestone's `## Log`.
- `wm close` closes a milestone only when every roadmap line is archived; dropped lines are gone from the roadmap and kept in the log.
- A change may say it comes after another; `wm status`, `wm instructions` and `wm pr` show each change's branch and base, `wm pr` targets the base, and `wm check` warns when a change is based on a branch that has already merged.
- The skills open a plan pull request for a new milestone, create each change's branch from its base before `wm new change`, and use the same branch names in every code repo of an atlas.
- Milestone behavior is described in a `milestones` spec.

## Non-goals

- A review of the milestone as a whole; each change is reviewed, and its agents already get the milestone's goal.
- A long-lived milestone branch that merges into `main` at the end.
- `wm` creating, switching, rebasing or pushing branches.
- Reconstructing a roadmap's history from git.
- Making milestones required; a change without one works as today.

## Roadmap

- [link-milestone-changes](../../../changes/archive/2026-11-17-link-milestone-changes/proposal.md): a `- Milestone:` line in the proposal, checked against the roadmap; `wm new change --milestone`; member changes' packs carry the milestone's Goal and Non-goals; a new `milestones` spec
- [add-milestone-log](../../../changes/archive/2026-11-17-add-milestone-log/proposal.md): `wm roadmap add`, `drop --reason` and `move`; hand edits to roadmap lines refused; a `## Log` in the milestone with records for added, dropped, moved, proposed and archived; `wm close` needs every line archived
- [add-change-dependencies](../../../changes/archive/2026-11-17-add-change-dependencies/proposal.md): a change says what it comes after; each change's branch and base shown in `wm status`, `wm instructions` and `wm pr`, with `wm pr` targeting the base; a warning for a change based on a merged branch; the plan pull request, branch creation and atlas branch names in the skills

## Log

- (archived) 2026-11-17 add-milestone-log by Noah Roberts
- (proposed) 2026-11-17 add-change-dependencies by Noah Roberts
- (archived) 2026-11-17 add-change-dependencies by Noah Roberts

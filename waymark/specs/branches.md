# Branches

## Purpose

Where a change's work lives in git: its branch, the branch it is based on, and the change it comes after. `wm` names and reports them; it never creates, switches, rebases or pushes a branch.

## Requirements

### Requirement: Change comes after another
A change's proposal MAY name one other change it comes after, in an `- After: <change>` line. `wm new change <name> --after <change>` SHALL write the line. For an active change, `wm check` SHALL report an error when the line names a change that is neither active nor archived, names the change itself, or forms a cycle with the lines of other active changes.

#### Scenario: Change written after another
- GIVEN an active change `add-limit`
- WHEN the planner runs `wm new change add-paging --after add-limit`
- THEN the proposal of `add-paging` has the line `- After: add-limit`

#### Scenario: Unknown change named
- GIVEN an active change whose proposal has `- After: no-such-change`
- WHEN `wm check` runs
- THEN it reports an error that names `no-such-change`

#### Scenario: Cycle
- GIVEN the active changes `add-a`, with `- After: add-b`, and `add-b`, with `- After: add-a`
- WHEN `wm check` runs
- THEN it reports an error on each that names the cycle

### Requirement: Branch and base
Every active change's branch SHALL be its name. Its base SHALL be the branch of the change it comes after, while that change is active and its branch isn't merged into the default branch; otherwise the base SHALL be the default branch. The default branch SHALL be the branch the `origin` remote's HEAD points at, or `main` when there is none.

#### Scenario: Change without a dependency
- GIVEN a repository whose `origin` HEAD is `main`, and an active change `add-limit` with no `- After:` line
- WHEN `wm instructions --change add-limit --json` runs
- THEN its branch is `add-limit` and its base is `main`

#### Scenario: Stacked change
- GIVEN an active change `add-limit` whose branch isn't merged, and an active change `add-paging` with `- After: add-limit`
- WHEN `wm instructions --change add-paging --json` runs
- THEN its branch is `add-paging` and its base is `add-limit`

### Requirement: Views show branch and base
`wm instructions` and `wm pr` SHALL give a change's branch and base, in their JSON and their text, and `wm pr`'s description SHALL be for a pull request into the base. `wm status` SHALL carry each active change's branch and base in its JSON, and in its text SHALL add an `on <base>` line under a change whose base isn't the default branch.

#### Scenario: Pull request of a stacked change
- GIVEN an active change `add-paging` based on the unmerged change `add-limit`
- WHEN `wm pr add-paging --json` runs
- THEN its `branch` is `add-paging` and its `base` is `add-limit`

#### Scenario: Status of a stacked change
- GIVEN the active changes `add-limit`, based on the default branch, and `add-paging`, based on `add-limit`
- WHEN `wm status` runs
- THEN the line for `add-paging` is followed by a line reading `on add-limit`, and no such line follows `add-limit`

### Requirement: Merged base reported
For an active change with an `- After:` line, `wm check` SHALL warn when the change it comes after is archived, or its branch is merged into the default branch, saying to rebase the change onto the default branch, retarget its pull request, and take the `- After:` line off. The change's base is then the default branch.

#### Scenario: Dependency merged
- GIVEN an active change `add-paging` with `- After: add-limit`, and `add-limit` archived
- WHEN `wm check` runs
- THEN it warns on `add-paging` that `add-limit` is merged, naming the rebase, the pull request and the `- After:` line, and `wm instructions --change add-paging --json` gives the default branch as its base

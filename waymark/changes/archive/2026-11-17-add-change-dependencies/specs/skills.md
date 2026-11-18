# Skills

## ADDED Requirements

### Requirement: Branches in the skills
The skills SHALL keep one branch shape. `wm-explore`, when it starts a milestone, SHALL put the milestone on its own branch and offer a plan pull request into the default branch before any member change is proposed. `wm-propose` SHALL create a change's branch from the base `wm` gives it before running `wm new change`, and SHALL pass `--after <change>` when the change needs another that isn't merged. `wm-apply` and `wm-pr` SHALL use the branch and base `wm` gives, and `wm-pr` SHALL open the pull request into the base. In an atlas, the skills SHALL use the same branch name in every repository a change touches.

#### Scenario: Milestone plan pull request
- GIVEN the installed `wm-explore` skill
- WHEN its steps for starting a milestone are read
- THEN they put the milestone on its own branch and offer a plan pull request into the default branch before a member change is proposed

#### Scenario: Branch before the change
- GIVEN the installed `wm-propose` skill
- WHEN its naming step is read
- THEN it creates the change's branch from its base before `wm new change`, and names `--after` for a change that needs an unmerged one

#### Scenario: Pull request into the base
- GIVEN the installed `wm-pr` skill
- WHEN its steps are read
- THEN it opens the pull request into the base `wm pr` gives

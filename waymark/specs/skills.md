# Skills

## Purpose

The skills `wm init` installs for the planner: the shape every one of them takes, so a session drafts and hands off the same way whichever skill it follows.

## Requirements

### Requirement: Skill layout
Every skill `wm init` installs SHALL have these sections, in this order: `## Role`, `## Inputs`, `## Steps`, `## Quality bar`, `## Show the human`, `## When to stop` and `## Rules`. A skill MAY add sections of its own between `## Steps` and `## Quality bar`, and no others. Its `## Rules` SHALL start with the line that points at the shared rules from `wm instructions`.

#### Scenario: Installed skills
- GIVEN a project where `wm init` has run
- WHEN each installed skill's `##` headings are read in order
- THEN each lists Role, Inputs, Steps, then any of its own sections, then Quality bar, Show the human, When to stop and Rules

#### Scenario: A section out of place
- GIVEN a skill whose `## When to stop` comes before `## Quality bar`
- WHEN the test over the shipped skills runs
- THEN it fails, naming the skill and the section out of place

### Requirement: Shipped skills
`wm init` SHALL install these skills and no others: `wm-kickoff`, `wm-explore`, `wm-propose`, `wm-update`, `wm-apply`, `wm-archive`, `wm-onboard` and `wm-pr`. Work of every size SHALL start from `wm-explore` or `wm-propose`; no skill is for tiny work alone.

#### Scenario: New project
- GIVEN a git repository with no record
- WHEN `wm init` runs for Claude Code
- THEN the installed skills are exactly those eight, and none is named `wm-fix`

### Requirement: Propose picks the path
The `wm-propose` skill SHALL have the planner read the specs and the code and choose the path itself, saying why, without asking the human which path to take:
- **tiny** when the work adds, changes or removes no requirement: the planner shows one line, what it will change and the requirement it keeps to, builds only after the human's yes, then checks, commits and offers a pull request;
- **short** only when the record and the human's words leave nothing to settle;
- **full** otherwise, with every question still open written under the design's `## Open questions`.

When tiny work turns out to change a requirement, the skill SHALL have the planner stop building and draft a change in the same session.

#### Scenario: Path chosen by the planner
- GIVEN the installed `wm-propose` skill
- WHEN its Steps are read
- THEN they tell the planner to choose tiny, short or full from what it found, and to wait for the human's yes before building tiny work

#### Scenario: Open questions
- GIVEN the installed `wm-propose` skill
- WHEN its Steps are read
- THEN they put a change with open questions on the full path, with the questions under the design's `## Open questions`

### Requirement: Explore's closing offers
The `wm-explore` skill SHALL close with four offers: do nothing, save an exploration, start a proposal of any size with `wm-propose`, or start a milestone.

#### Scenario: No tiny-path offer
- GIVEN the installed `wm-explore` skill
- WHEN its closing offers are read
- THEN there are four, and none names `wm-fix`

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

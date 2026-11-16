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

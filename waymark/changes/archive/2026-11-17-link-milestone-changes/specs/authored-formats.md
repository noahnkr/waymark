# Authored formats

## MODIFIED Requirements

### Requirement: Proposal facts as a list
A proposal's facts SHALL be bullet lines between its title and its first section: `- Owner: <name>`, and optionally `- Milestone: <name>`, `- Review: <level>` and `- Path: short`. `wm new change` SHALL write them so. A fact written without the bullet SHALL NOT be read as a fact.

#### Scenario: New change
- GIVEN a project with git user Ada
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- Owner: Ada` and `- Path: short` under its title

#### Scenario: Fact without a bullet
- GIVEN an active change whose proposal has the line `Owner: Ada` without a bullet, and no `- Owner:` line
- WHEN `wm check` runs
- THEN it reports that the proposal has no owner, and no message names `wm update`

## REMOVED Requirements

### Requirement: Milestone as one file
Reason: Moved to the `milestones` spec unchanged, so every milestone requirement is in one spec.

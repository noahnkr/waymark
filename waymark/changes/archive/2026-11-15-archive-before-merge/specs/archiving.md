# Archiving

## Purpose

When a change is archived, and how its pull request is described once it is. The archive goes on the change's own branch, before the pull request, so the code, the merged specs and the archived change are reviewed and merged together.

## ADDED Requirements

### Requirement: Archive before the pull request
When every item of a change is built and the change is reviewed, `wm instructions` SHALL make the next step the archive, and SHALL say that it is taken on the change's branch before the pull request is opened, when the human decides. It SHALL NOT say that the archive waits for a merge.

#### Scenario: Built and reviewed
- GIVEN an accepted change with every item ticked and its review recorded
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is the archive, the guidance says to archive on the change's branch before the pull request, and nothing in it mentions waiting for a merge

### Requirement: Pull request for an archived change
`wm pr` SHALL describe a change that is archived in the record as it describes an active one: the title, the description, the specs, the items and the review. It SHALL add the change's outcome, and link to the archived proposal. When the name is in the archive more than once, it SHALL describe the latest.

#### Scenario: Archived on its branch
- GIVEN a change that was reviewed and then archived with an outcome
- WHEN `wm pr <change>` runs
- THEN the description holds the change's why, what changes, specs, items, review and outcome, and its link points at the proposal in the archived folder

#### Scenario: Neither active nor archived
- GIVEN no active or archived change named `add-order`
- WHEN `wm pr add-order` runs
- THEN it is refused, and the reason names the active changes

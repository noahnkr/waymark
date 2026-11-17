# Setup

## ADDED Requirements

### Requirement: Retired skills removed
`wm init` and `wm update` SHALL remove every skill folder whose name starts with `wm-` and that the running `wm` doesn't ship, from the shared skills folder and from each listed agent tool's skills folder, and SHALL list each removed file as removed. Folders whose names don't start with `wm-` SHALL be left as they are.

#### Scenario: Skill retired
- GIVEN a machine set up by a `wm` that shipped `wm-fix`, with `wm-fix` in the shared skills folder and in Claude Code's
- WHEN `wm update` runs
- THEN both `wm-fix` folders are gone, and the output lists their files as removed

#### Scenario: The project's own skill
- GIVEN a Claude Code skills folder holding a skill named `release-notes` that `wm` didn't write
- WHEN `wm init` runs
- THEN the `release-notes` folder is unchanged

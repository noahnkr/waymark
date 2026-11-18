# Agent guidance

## ADDED Requirements

### Requirement: Project rules in every pack
`wm context` SHALL give the charter's Rules whole in every pack, for explore, implement and review alike, as `rules`, a string, in the JSON output, and under "Project rules" in the text output.

#### Scenario: Reviewer gets every rule
- GIVEN a charter whose Rules hold `1. Never hand-edit generated docs.`, and a change waiting for its independent review
- WHEN the planner runs `wm context --for review <change> --json`
- THEN `rules` holds `1. Never hand-edit generated docs.`

# Authored formats

## MODIFIED Requirements

### Requirement: Structured outcome
`wm archive` SHALL take `--built` and `--differs` instead of `--outcome`, each one or more times, and SHALL write them under the archived proposal's `## Outcome` as a `- **Built:**` and a `- **Differs:**` line. A value given once SHALL be written on its label's line, as `- **Built:** <text>`. Several values SHALL be written as nested bullets under the label, one per value, in the order given. `--differs` MAY be left out, and SHALL then be written as `none`. `wm pr` SHALL show both, with their nested bullets.

#### Scenario: Archived with an outcome
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has the lines `- **Built:** The result limit.` and `- **Differs:** Fifty, not twenty.`

#### Scenario: Nothing differs
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit."`
- THEN the archived proposal's Outcome has the line `- **Differs:** none`

#### Scenario: Outcome as a list
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --built "A flag to change it." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has `- **Built:**`, then `  - The result limit.` and `  - A flag to change it.`, then `- **Differs:** Fifty, not twenty.`

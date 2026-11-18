# Agent guidance

## ADDED Requirements

### Requirement: Background in the packs
`wm context --for implement` and `wm context --for review` SHALL hold, for each spec the change has a delta for, the spec's Background as it will read once the change is archived: the delta's Background when the delta has one, otherwise the spec's. A spec with neither SHALL be left out. The text and JSON outputs SHALL hold the same Backgrounds.

#### Scenario: Background of a touched spec
- GIVEN an accepted change with a delta for `lead-nurture` and none for `ats`, where both specs have a Background
- WHEN the planner runs `wm context --for implement <change> 1.1 --json`
- THEN the pack holds `lead-nurture`'s Background and not `ats`'s

#### Scenario: Background from the delta
- GIVEN an accepted change whose delta for `lead-nurture` has a Background that differs from the spec's
- WHEN the planner runs `wm context --for review <change>`
- THEN the pack shows the delta's Background for `lead-nurture`, and not the spec's

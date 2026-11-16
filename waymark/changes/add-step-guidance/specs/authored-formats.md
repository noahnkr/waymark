# Authored formats

## ADDED Requirements

### Requirement: Items say how they are done
Every task item of an active change SHALL have a `- Criteria:` line and a `- Verify:` line. `wm check` SHALL report an item without one of them, naming the line it lacks.

#### Scenario: Item without verification
- GIVEN an active change whose item 1.2 has a `- Criteria:` line and no `- Verify:` line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- Verify:`

### Requirement: Decisions weigh options
Every decision in an active change's design SHALL name at least two options under `- Options:`: two or more nested bullets, or one line naming them joined by "or" or ";". `wm check` SHALL report a decision with fewer than two.

#### Scenario: One option
- GIVEN an active change whose design has a decision with the line `- Options: cut after sorting`
- WHEN `wm check` runs
- THEN it reports an error on that decision that asks for at least two options

#### Scenario: Options as a list
- GIVEN an active change whose design has a decision whose `- Options:` line is followed by two bullets
- WHEN `wm check` runs
- THEN it reports no problem with that decision's options

# Authored formats

## MODIFIED Requirements

### Requirement: Items say how they are done
Every task item of an active change SHALL have a `- **Build:**` line, a `- **Criteria:**` line and a `- **Verify:**` line. The Build line SHALL be `planner`, `implementer` or `human`. `wm check` SHALL report an item without one of them, naming the line it lacks.

#### Scenario: Item without verification
- GIVEN an active change whose item 1.2 has a Build line and a Criteria line, and no Verify line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Verify:**`

#### Scenario: Item without a Build line
- GIVEN an active change whose item 1.2 has a Criteria line and a Verify line, and no Build line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Build:**` and the values `planner`, `implementer` and `human`

### Requirement: Item lines in order
A task item's label lines SHALL come in the order `Build`, `Repo`, `Criteria`, `Verify`, before any record under the item; `Repo` MAY be left out. `wm check` SHALL report as an error, in an active change, an item whose label lines are in another order, naming the order.

#### Scenario: Build line last
- GIVEN an active change whose item 1.2 has its `- **Criteria:**` and `- **Verify:**` lines, then `- **Build:** implementer`
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names the order Build, Repo, Criteria, Verify

#### Scenario: Lines in order
- GIVEN an active change whose item 1.2 has `- **Build:** planner`, `- **Criteria:**` with two bullets, and `- **Verify:**`, in that order
- WHEN `wm check` runs
- THEN it reports no problem on item 1.2

# Building

## MODIFIED Requirements

### Requirement: Planner builds its items
When the next step of an accepted change is to apply an item with the line `- **Build:** planner`, `wm instructions` SHALL tell the planner to build the item itself from the item's context pack. It SHALL also tell the planner to run the checks the item touches, and to record the result with `wm tick`, `wm block` or `wm gap`.

#### Scenario: Item built by the planner
- GIVEN an accepted change whose next step applies item 1.1, which has the line `- **Build:** planner`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to build item 1.1 itself and tick it, and doesn't mention starting an implementer

### Requirement: Build line
Every task item SHALL carry a `- **Build:**` line, first among its lines: `planner` for an item the planner builds, or `delegate` for an item a fresh implementer builds. When the next step applies an item with `- **Build:** delegate`, `wm instructions` SHALL tell the planner to start an implementer with the change and item and nothing else. `wm check` SHALL report any other value of `Build:` as an error that names `planner` and `delegate`, and a build tag at the end of an item's title as an old layout.

#### Scenario: Tagged item
- GIVEN an accepted change whose next step applies item 1.2, which has the line `- **Build:** delegate`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to start an implementer for item 1.2 with the change and item and nothing else

#### Scenario: Unknown build value
- GIVEN a task item with the line `- **Build:** someone`
- WHEN `wm check` runs
- THEN it reports an error on that item that names `planner` and `delegate` as the values

### Requirement: Build line accepted with the item
An item's Build line SHALL be part of the item's definition that the human accepts. Changing its value SHALL withdraw acceptance, as changing any other part of the item's definition does.

#### Scenario: Build changed after acceptance
- GIVEN an accepted change whose item 1.2 has `- **Build:** planner`
- WHEN the line is changed to `- **Build:** delegate`
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

## RENAMED Requirements

- From: Planner builds by default
- To: Planner builds its items
- From: Delegation tag
- To: Build line
- From: Delegation tag accepted with the item
- To: Build line accepted with the item

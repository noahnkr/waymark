# Building

## Modified requirements

### Requirement: Delegation tag
A task item MAY carry the line `- Build: delegate` under it. When the next step applies an item with that line, `wm instructions` SHALL tell the planner to start an implementer with the change and item and nothing else. `wm check` SHALL report any other value of `Build:` as an error, and a build tag at the end of an item's title as an old layout that names `wm update`.

#### Scenario: Tagged item
- GIVEN an accepted change whose next step applies item 1.2, which has the line `- Build: delegate`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to start an implementer for item 1.2 with the change and item and nothing else

#### Scenario: Unknown build value
- GIVEN a task item with the line `- Build: someone`
- WHEN `wm check` runs
- THEN it reports an error on that item that names `delegate` as the only value

### Requirement: Delegation tag accepted with the item
An item's `Build:` line SHALL be part of the item's definition that the human accepts. Adding, removing or changing it SHALL withdraw acceptance, as changing any other part of the item's definition does.

#### Scenario: Tag added after acceptance
- GIVEN an accepted change
- WHEN `- Build: delegate` is added under one of its items
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

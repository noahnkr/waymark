# Building

## Purpose

Who builds a task item of an accepted change, named by the item's role. The planner builds most items, working with the human in the session. An `implementer` item is built by a fresh implementer from the record alone, and a `human` item is done by the human, who confirms it to the planner.

## Requirements

### Requirement: Planner builds its items
When the next step of an accepted change is to apply an item with the line `- **Build:** planner`, `wm instructions` SHALL tell the planner to build the item itself from the item's context pack. It SHALL also tell the planner to run the checks the item touches, and to record the result with `wm tick`, `wm block` or `wm gap`.

#### Scenario: Item built by the planner
- GIVEN an accepted change whose next step applies item 1.1, which has the line `- **Build:** planner`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to build item 1.1 itself and tick it, and doesn't mention starting an implementer

### Requirement: Build line
Every task item SHALL carry a `- **Build:**` line, first among its lines, naming the role that builds it: `planner` for an item the planner builds, `implementer` for an item a fresh implementer builds, or `human` for an item only the human can do. When the next step applies an item with `- **Build:** implementer`, `wm instructions` SHALL tell the planner to start an implementer with the change and item and nothing else. `wm check` SHALL report any other value of `Build:`, `delegate` included, as an error that names `planner`, `implementer` and `human`, and a build tag at the end of an item's title as an old layout. `wm show --json` SHALL give each item's role as `build`.

#### Scenario: Implementer item
- GIVEN an accepted change whose next step applies item 1.2, which has the line `- **Build:** implementer`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to start an implementer for item 1.2 with the change and item and nothing else

#### Scenario: Unknown build value
- GIVEN a task item with the line `- **Build:** delegate`
- WHEN `wm check` runs
- THEN it reports an error on that item that names `planner`, `implementer` and `human` as the values

#### Scenario: Role in the JSON
- GIVEN an active change whose item 1.1 has `- **Build:** planner` and item 1.2 `- **Build:** human`
- WHEN the planner runs `wm show <change> --json`
- THEN item 1.1 has `"build": "planner"` and item 1.2 `"build": "human"`, and neither has a `delegate` field

### Requirement: Build line accepted with the item
An item's Build line SHALL be part of the item's definition that the human accepts. Changing its value SHALL withdraw acceptance, as changing any other part of the item's definition does.

#### Scenario: Build changed after acceptance
- GIVEN an accepted change whose item 1.2 has `- **Build:** planner`
- WHEN the line is changed to `- **Build:** implementer`
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

### Requirement: Planner edits in an atlas
In an atlas, the planner SHALL be able to edit a file in any code repo, whether or not a change is being built there. An implementer SHALL still edit only in the code repo its item names, and the planner MAY edit the record at any time, as before.

#### Scenario: Repo of the item being built
- GIVEN an atlas with an accepted change whose next item to build names the repo `api`
- WHEN the planner edits a file in `api`
- THEN the edit is allowed

#### Scenario: Another repo
- GIVEN the same atlas and change
- WHEN the planner edits a file in the repo `web`, which no item being built names
- THEN the edit is allowed

#### Scenario: Implementer in another repo
- GIVEN the same atlas and change
- WHEN an implementer edits a file in the repo `web`
- THEN the edit is refused with a reason that names `api` as the repo it may edit now

### Requirement: Human does their items
When the next step of an accepted change is to apply an item with the line `- **Build:** human`, `wm instructions` SHALL tell the planner to show the human the item's criteria and verification as the steps to take, to tick the item with `wm tick` only after the human says it is done, and, when the human can't do it now, to record what it waits on with `wm block` so that the change's other items can go on. It SHALL NOT tell the planner to build the item, or to start an implementer.

#### Scenario: Item for the human
- GIVEN an accepted change whose next step applies item 1.2, which has the line `- **Build:** human`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to give the human item 1.2's steps and to tick it after their yes, names `wm tick` and `wm block`, and doesn't mention starting an implementer

#### Scenario: Human item waits
- GIVEN an accepted change with items 1.1, 1.2 and 1.3, none ticked, where 1.2 has `- **Build:** human`
- WHEN item 1.1 is ticked and the planner runs `wm block <change> 1.2 "waiting for the DNS record"`
- THEN `wm instructions --change <change>` offers item 1.3 to apply

### Requirement: No implementer for a human item
An implementer started on an item with `- **Build:** human` SHALL be refused, with a reason that says the human does the item and the planner ticks it after their yes.

#### Scenario: Implementer on a human item
- GIVEN an accepted change whose next item to apply, 1.2, has `- **Build:** human`
- WHEN the planner starts an implementer with the prompt `<change> 1.2`
- THEN it is refused with a reason that says the human does item 1.2

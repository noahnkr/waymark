# Building

## Purpose

Who builds a task item of an accepted change. By default the planner builds it, working with the human in the session. An item tagged for delegation is built by a fresh implementer instead, from the record alone.

## Added requirements

### Requirement: Planner builds by default
When the next step of an accepted change is to apply an item that isn't tagged for delegation, `wm instructions` SHALL tell the planner to build the item itself from the item's context pack. It SHALL also tell the planner to run the checks the item touches, and to record the result with `wm tick`, `wm block` or `wm gap`.

#### Scenario: Untagged item
- GIVEN an accepted change whose next step applies item 1.1, which has no build tag
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to build item 1.1 itself and tick it, and doesn't mention starting an implementer

### Requirement: Delegation tag
A task item MAY carry the tag `build: delegate` on its line, next to its review level and in either order. When the next step applies a tagged item, `wm instructions` SHALL tell the planner to start an implementer with the change and item and nothing else. `wm check` SHALL report any other value of the build tag as an error.

#### Scenario: Tagged item
- GIVEN an accepted change whose next step applies item 1.2, tagged `build: delegate`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the guidance tells the planner to start an implementer for item 1.2 with the change and item and nothing else

#### Scenario: Unknown build tag
- GIVEN a task item tagged `build: someone`
- WHEN `wm check` runs
- THEN it reports an error on that item that names `delegate` as the only value

### Requirement: Delegation tag accepted with the item
An item's build tag SHALL be part of the item's definition that the human accepts. Adding, removing or changing it SHALL withdraw acceptance, as changing its review level does.

#### Scenario: Tag added after acceptance
- GIVEN an accepted change
- WHEN `build: delegate` is added to one of its items
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

### Requirement: Planner edits in an atlas
In an atlas, the agent tool's edit hook SHALL let the planner edit a file in a code repo while an accepted change has an item being built that names that repo, and refuse an edit in any other code repo with the reason. The planner MAY edit the record at any time, as before.

#### Scenario: Repo of the item being built
- GIVEN an atlas with an accepted change whose next item to build names the repo `api`
- WHEN the planner edits a file in `api`
- THEN the edit is allowed

#### Scenario: Another repo
- GIVEN the same atlas and change
- WHEN the planner edits a file in the repo `web`, which no item being built names
- THEN the edit is refused with a reason that names `api` as the repo it may edit now

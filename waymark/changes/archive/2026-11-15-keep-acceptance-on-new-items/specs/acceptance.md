# Acceptance

## Purpose

What the human's acceptance of a change covers, and which edits withdraw it. Only the human accepts, with `wm accept`, and nothing in a change is built before it.

## ADDED Requirements

### Requirement: Acceptance covers what was accepted
An acceptance SHALL cover the change's proposal, its deltas, its design, the living text of the requirements its deltas modify or remove, the change's review level, and the definition of each task item it names. Changing any of these, or removing an item it names, SHALL withdraw the acceptance, and `wm status` SHALL ask the human to accept again. Ticks, blockers, notes and review records SHALL NOT withdraw it.

#### Scenario: Accepted item edited
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN the criteria of item 1.2 are changed
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

#### Scenario: Accepted item removed
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN item 1.2 is removed from the task list
- THEN the change is no longer accepted

### Requirement: Items added after acceptance
`wm accept` SHALL write the numbers of the change's items into the acceptance line, as `items: <number> <number>...` after the fingerprint. A task item added after the acceptance SHALL NOT withdraw it, and SHALL be built like any other item. Accepting the change again SHALL cover every item it then has. Syncing a change SHALL keep the list.

#### Scenario: Item added
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN item 1.3 is appended to the task list
- THEN the change is still accepted, and once 1.1 and 1.2 are ticked, `wm instructions` makes 1.3 the next item to apply

#### Scenario: Accepted again
- GIVEN an accepted change with item 1.3 added after its acceptance, whose design is then edited
- WHEN the human runs `wm accept <change>`
- THEN the acceptance line names items 1.1, 1.2 and 1.3

### Requirement: Acceptance without an item list
An acceptance line without an item list, written by an older `wm`, SHALL cover every item the change has, so adding an item withdraws it as before. `wm check` SHALL NOT report such a line as malformed.

#### Scenario: Older acceptance line
- GIVEN an accepted change whose acceptance line has a fingerprint and no item list
- WHEN an item is appended to its task list
- THEN the change is no longer accepted, and `wm check` reports no malformed evidence

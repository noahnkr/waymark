# Acceptance

## MODIFIED Requirements

### Requirement: Items added after acceptance
`wm accept` SHALL write the numbers of the change's items into the `(accepted)` record, as `items <number>, <number>...` after the fingerprint. A task item added after the acceptance SHALL NOT withdraw it, and SHALL be built like any other item. Accepting the change again SHALL add a new `(accepted)` record that covers every item it then has, and the latest `(accepted)` record SHALL be the one that counts. Syncing a change SHALL keep the list.

#### Scenario: Item added
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN item 1.3 is appended to the task list
- THEN the change is still accepted, and once 1.1 and 1.2 are ticked, `wm instructions` makes 1.3 the next item to apply

#### Scenario: Accepted again
- GIVEN an accepted change with item 1.3 added after its acceptance, whose design is then edited
- WHEN the human runs `wm accept <change>`
- THEN the Log holds a second `(accepted)` record ending `items 1.1, 1.2, 1.3 by <who>`, after the first

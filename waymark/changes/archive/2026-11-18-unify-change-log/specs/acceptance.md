# Acceptance

## MODIFIED Requirements

### Requirement: Acceptance covers what was accepted
An acceptance SHALL cover the change's proposal, its deltas, its design, the living text of the requirements its deltas modify or remove, the change's review level, and the definition of each task item it names. Changing any of these, or removing an item it names, SHALL withdraw the acceptance, and `wm status` SHALL ask the human to accept again. Ticks and records SHALL NOT withdraw it.

#### Scenario: Accepted item edited
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN the criteria of item 1.2 are changed
- THEN the change is no longer accepted, and `wm status` asks the human to accept it again

#### Scenario: Accepted item removed
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN item 1.2 is removed from the task list
- THEN the change is no longer accepted

#### Scenario: Record added
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN `wm block <change> 1.2 "<reason>"` adds a `(blocked)` record for item 1.2 to the Log
- THEN the change is still accepted

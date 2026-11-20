# Acceptance

## MODIFIED Requirements

### Requirement: Items added after acceptance
`wm accept` SHALL write the numbers of the change's items into the `(accepted)` record, as `items <number>, <number>...` after the fingerprint. A task item added after the acceptance SHALL NOT withdraw it, and SHALL be built like any other item. Accepting the change again SHALL add a new `(accepted)` record that covers every item it then has, and the latest `(accepted)` record SHALL be the one that counts. Syncing a change SHALL keep the list.

#### Scenario: Item added
- GIVEN an accepted change whose acceptance names items 1.1 and 1.2
- WHEN item 1.3 is appended to the task list
- THEN the change is still accepted, and once 1.1 and 1.2 are ticked, `wm instructions` makes 1.3 the next item to apply

#### Scenario: Accepted again
- GIVEN an accepted change with item 1.3 added after its acceptance, whose design is then edited and the edit recorded with `wm revise <change> "<why>" --parts design`
- WHEN the human runs `wm accept <change>`
- THEN the Log holds a second `(accepted)` record ending `items 1.1, 1.2, 1.3 by <who>`, after the first

## ADDED Requirements

### Requirement: Revisions recorded
`wm revise <change> "<why>"` SHALL write `<date> (revised) [<part>, <part>...] by <who>: <why>` into the change's Log, where `--parts` names the parts the revision changed: item numbers, `proposal`, `design` or `specs/<area>`. It SHALL refuse a part that isn't an item, a delta of the change, `proposal` or `design`, and a change that has never been accepted. `wm accept` SHALL refuse to accept a change that has an `(accepted)` record and no `(revised)` record after the last one, with a reason that names `wm revise`.

#### Scenario: Revision recorded
- GIVEN an accepted change with item 2.2, and a git user named Ada
- WHEN the planner edits item 2.2's criteria and runs `wm revise <change> "the count was 2, not 11" --parts 2.2` on 2026-11-20
- THEN the Log ends with `2026-11-20 (revised) 2.2 by planner for Ada: the count was 2, not 11`

#### Scenario: Accepting again without a revision
- GIVEN an accepted change whose design was edited after it was accepted, and no `(revised)` record since
- WHEN the human runs `wm accept <change>`
- THEN it is refused with a reason that names `wm revise`, and nothing is written

#### Scenario: Accepting again after a revision
- GIVEN the same change, with `wm revise <change> "<why>" --parts design` run after the edit
- WHEN the human runs `wm accept <change>`
- THEN a second `(accepted)` record is written after the `(revised)` record

#### Scenario: Unknown part
- GIVEN an accepted change with items 1.1 and 1.2 and a delta for `search`
- WHEN the planner runs `wm revise <change> "<why>" --parts 3.1`
- THEN it is refused with a reason that names item 3.1, and nothing is written

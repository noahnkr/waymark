# Acceptance

## ADDED Requirements

### Requirement: Revised item left ticked
In an active change, `wm check` SHALL warn when a `(revised)` record names an item that was ticked when the revision was recorded, and no `(ticked)` or `(reopened)` record for that item follows it. The warning SHALL name the item and say to reopen it with `wm reopen <change> <item> --reason "<why>"`, or tick it again once its new criteria hold.

#### Scenario: Revised item still ticked
- GIVEN an accepted change with item 2.3 ticked, whose Log then holds `(revised) 2.3` and no later `(ticked)` or `(reopened)` record for 2.3
- WHEN `wm check` runs
- THEN it warns that item 2.3 was revised after it was ticked, and names `wm reopen`

#### Scenario: Revised item reopened
- GIVEN the same change, with `wm reopen <change> 2.3 --reason "<why>"` run after the revision
- WHEN `wm check` runs
- THEN it reports nothing about item 2.3

#### Scenario: Revised item not yet ticked
- GIVEN an accepted change whose Log holds `(revised) 2.3` while item 2.3 was not ticked
- WHEN `wm check` runs
- THEN it reports nothing about item 2.3

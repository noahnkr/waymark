# Records

## MODIFIED Requirements

### Requirement: Item records
`wm` SHALL write the records about one item into the change's `## Log`, naming the item straight after the kind: `(ticked)` from `wm tick` and from an implementer's `done` ending, `(blocked)` from `wm block`, `(gap)` from `wm gap`, `(note)` from `wm note`, `(reopened)` from `wm reopen`, with the reason given as its text when there is one, and `(resolved)` from `wm resolve <change> <item>`. An item SHALL be blocked while the Log has a `(blocked)` or `(gap)` record for it with no `(resolved)` record for it after that one. Resolving an item SHALL add the `(resolved)` record and keep the records it resolves. An item's tick SHALL stay its checkbox, and a `(ticked)` record SHALL NOT withdraw acceptance.

#### Scenario: Blocked item
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm block <change> 1.2 "the API key is missing"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (blocked) 1.2 by planner for Ada: the API key is missing`, and nothing is written under item 1.2

#### Scenario: Resolved item keeps its blocker
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.2 by planner for Ada: the API key is missing`
- WHEN the human runs `wm resolve <change> 1.2 "use the test key"` on 2026-11-21
- THEN the Log holds the `(blocked)` record and, after it, `2026-11-21 (resolved) 1.2 by <who>: use the test key`, and `wm instructions` offers item 1.2 to apply

#### Scenario: Records for two items
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.1 by Ada: <reason>`, then `2026-11-20 (blocked) 1.2 by Ada: <reason>`
- WHEN the human runs `wm resolve <change> 1.2 "<text>"`
- THEN item 1.2 is no longer blocked, and item 1.1 still is

#### Scenario: Planner's item ticked
- GIVEN an accepted change whose item 1.1 has `- **Build:** planner`, and a git user named Ada
- WHEN the planner runs `wm tick <change> 1.1` on 2026-11-20
- THEN item 1.1 is ticked, the Log ends with `2026-11-20 (ticked) 1.1 by planner for Ada`, and the change is still accepted

#### Scenario: Human's item ticked
- GIVEN an accepted change whose item 1.2 has `- **Build:** human`, and a git user named Ada
- WHEN the planner runs `wm tick <change> 1.2` on 2026-11-20, after Ada says it is done
- THEN the Log ends with `2026-11-20 (ticked) 1.2 by Ada`

#### Scenario: Implementer's item ticked
- GIVEN an accepted change with item 1.3 not ticked
- WHEN its implementer ends with `ITEM: <change> 1.3` and `RESULT: done: <note>` on 2026-11-20
- THEN item 1.3 is ticked, and the Log ends with `2026-11-20 (ticked) 1.3 by implementer`


#### Scenario: Reopened with a reason
- GIVEN an accepted change with item 1.2 ticked and no open review naming it, and a git user named Ada
- WHEN the planner runs `wm reopen <change> 1.2 --reason "its criteria changed"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (reopened) 1.2 by planner for Ada: its criteria changed`

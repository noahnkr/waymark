# Records

## MODIFIED Requirements

### Requirement: One record shape
Every line `wm` writes as evidence SHALL be a record of the shape `<YYYY-MM-DD> (<kind>) [<args>] [by <who>]: <text>`, with the kind straight after the date, then the kind's arguments, then who wrote it. A list of items among the arguments SHALL be separated by `, `, and a list that another argument follows SHALL end with `;`. Who wrote it SHALL run to the `: ` or the end of the line, so it may hold spaces; `--by` SHALL refuse a value that holds `: `. A record with no text, such as `(reopened)`, SHALL end after who wrote it. In an active change, `wm check` SHALL report as an error a line that starts like a record and doesn't have this shape, naming the shape it expected.

#### Scenario: Record in its shape
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm block <change> 1.2 "the API key is missing"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (blocked) 1.2 by planner for Ada: the API key is missing`

#### Scenario: Malformed record
- GIVEN an active change whose Log holds the line `(blocked) 1.2 the API key is missing`
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (blocked) <item> [by <who>]: <reason>`

#### Scenario: Kind before the date
- GIVEN an active change whose Log holds the line `(blocked) 2026-11-20 1.2 by Ada: the API key is missing`
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (blocked) <item> [by <who>]: <reason>`

#### Scenario: Item list without commas
- GIVEN an active change whose Log holds `2026-11-20 (accepted) fingerprint <digest> items 1.1 1.2 by Ada`
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (accepted) fingerprint <digest> items <item>, <item>... [by <who>]`

### Requirement: Who wrote a record
A record SHALL name who wrote it, by its kind:
- the human's acts, `(accepted)`, `(override)`, `(resolved)`, `(archived)`, and `(ticked)` for an item with `- **Build:** human`, SHALL name the git user;
- what the planner writes, `(note)`, `(blocked)`, `(gap)`, `(reopened)`, `(self-review)`, `(synced)`, `(revised)`, `(ticked)` for any other item, and a milestone's `(added)`, `(dropped)`, `(moved)` and `(proposed)`, SHALL name `planner for <git user>`, or `planner` when no git user is set;
- a record written from an agent's ending SHALL name `implementer` or `reviewer`.

Every command that writes a record SHALL accept `--by <who>`, and `--by` SHALL take the place of who the kind names. A human act with no git user and no `--by` SHALL be written without the `by` part. `wm accept` SHALL still refuse without a git user, as before. An implementer's `wm note` without `--by implementer` SHALL be refused, with a reason that says to add it. Records already written SHALL be read as they are.

#### Scenario: Planner's note
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm note <change> 1.2 "the parser is done"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (note) 1.2 by planner for Ada: the parser is done`

#### Scenario: Human's acceptance
- GIVEN a change ready to accept, and a git user named Ada
- WHEN the human runs `wm accept <change>` on 2026-11-20
- THEN the `(accepted)` record ends `by Ada`

#### Scenario: Reviewer's verdict
- GIVEN a change with items 1.1 and 1.2, waiting for an independent review
- WHEN its reviewer ends with `CHANGE: <change>` and `VERDICT: pass: <reasons>` on 2026-11-20
- THEN the change's Log holds `2026-11-20 (review) pass covers 1.1, 1.2 by reviewer: <reasons>`

#### Scenario: Explicit author
- GIVEN an accepted change with items 1.1 and 1.2, every item ticked, at review level `self`
- WHEN the planner runs `wm review <change> --self "<summary>" --by "Ada and Grace"`
- THEN the self-review record reads `<date> (self-review) covers 1.1, 1.2 by Ada and Grace: <summary>`

#### Scenario: Implementer's note without --by
- GIVEN an implementer building item 1.2
- WHEN it runs `wm note <change> 1.2 "the parser is done"`
- THEN it is refused with a reason that names `--by implementer`, and nothing is written

### Requirement: Item records
`wm` SHALL write the records about one item into the change's `## Log`, naming the item straight after the kind: `(ticked)` from `wm tick` and from an implementer's `done` ending, `(blocked)` from `wm block`, `(gap)` from `wm gap`, `(note)` from `wm note`, `(reopened)` from `wm reopen` and `(resolved)` from `wm resolve <change> <item>`. An item SHALL be blocked while the Log has a `(blocked)` or `(gap)` record for it with no `(resolved)` record for it after that one. Resolving an item SHALL add the `(resolved)` record and keep the records it resolves. An item's tick SHALL stay its checkbox, and a `(ticked)` record SHALL NOT withdraw acceptance.

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

### Requirement: Log section
`wm` SHALL write every record of a change into a `## Log` section, the last section of the change's task list, creating the section when needed, in the order the records are written: the records about the change as a whole, `(accepted)`, `(revised)`, `(synced)`, `(override)`, `(self-review)`, `(review)`, `(resolved)` for the review and `(archived)`, and the records about one item. The acceptance SHALL read `<date> (accepted) fingerprint <digest> items <number>, <number>... by <who>`. The proposal SHALL hold no records, and an item SHALL hold only its definition and its tick. `wm check` SHALL report as an error, in an active change, a `## Log` section that isn't the last, or a record outside it, saying it belongs in the Log.

#### Scenario: Acceptance in the Log
- GIVEN a change whose task list has items 1.1 and 1.2 and no Log section
- WHEN the human, Ada, runs `wm accept <change>` on 2026-11-20
- THEN the task list ends with a `## Log` section holding `2026-11-20 (accepted) fingerprint <digest> items 1.1, 1.2 by Ada`, and the proposal is unchanged

#### Scenario: Record under an item
- GIVEN an active change with the line `2026-11-20 (note) by Ada: <text>` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that says records belong in the Log

### Requirement: Item records shown with their item
`wm show <change>`, in text and JSON, and the implement context pack SHALL show each item's records with that item, gathered from the change's `## Log` in the order they were written. `wm show` SHALL also show the Log as written.

#### Scenario: Blocker shown with its item
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.2 by planner for Ada: the API key is missing`
- WHEN the planner runs `wm show <change> --json`
- THEN item 1.2's records hold that `(blocked)` record, and item 1.1's hold none

#### Scenario: Note in the implementer's pack
- GIVEN an accepted change whose Log holds `2026-11-20 (note) 1.2 by implementer: partial: the parser is done`
- WHEN the planner runs `wm context <change> 1.2 --for implement`
- THEN the pack shows the note as a note from earlier work on item 1.2

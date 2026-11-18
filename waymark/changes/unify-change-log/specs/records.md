# Records

## ADDED Requirements

### Requirement: Item records shown with their item
`wm show <change>`, in text and JSON, and the implement context pack SHALL show each item's records with that item, gathered from the change's `## Log` in the order they were written. The review context pack and `wm show` SHALL also show the Log as written.

#### Scenario: Blocker shown with its item
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.2 by Ada: the API key is missing`
- WHEN the planner runs `wm show <change> --json`
- THEN item 1.2's records hold that `(blocked)` record, and item 1.1's hold none

#### Scenario: Note in the implementer's pack
- GIVEN an accepted change whose Log holds `2026-11-20 (note) 1.2 by wm-implementer: partial: the parser is done`
- WHEN the planner runs `wm context <change> 1.2 --for implement`
- THEN the pack shows the note as a note from earlier work on item 1.2

## MODIFIED Requirements

### Requirement: Item records
`wm` SHALL write the records about one item into the change's `## Log`, naming the item straight after the kind: `(blocked)` from `wm block`, `(gap)` from `wm gap`, `(note)` from `wm note`, `(reopened)` from `wm reopen` and `(resolved)` from `wm resolve <change> <item>`. An item SHALL be blocked while the Log has a `(blocked)` or `(gap)` record for it with no `(resolved)` record for it after that one. Resolving an item SHALL add the `(resolved)` record and keep the records it resolves.

#### Scenario: Blocked item
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm block <change> 1.2 "the API key is missing"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (blocked) 1.2 by Ada: the API key is missing`, and nothing is written under item 1.2

#### Scenario: Resolved item keeps its blocker
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.2 by Ada: the API key is missing`
- WHEN the human runs `wm resolve <change> 1.2 "use the test key"` on 2026-11-21
- THEN the Log holds the `(blocked)` record and, after it, `2026-11-21 (resolved) 1.2 by <who>: use the test key`, and `wm instructions` offers item 1.2 to apply

#### Scenario: Records for two items
- GIVEN an accepted change whose Log holds `2026-11-20 (blocked) 1.1 by Ada: <reason>`, then `2026-11-20 (blocked) 1.2 by Ada: <reason>`
- WHEN the human runs `wm resolve <change> 1.2 "<text>"`
- THEN item 1.2 is no longer blocked, and item 1.1 still is

### Requirement: Notes written with wm note
`wm note <change> <item> "<text>"` SHALL write a `(note)` record naming the item into the `## Log` of an accepted change whose item isn't ticked. It SHALL refuse an item that is already ticked, and a change that isn't accepted. A note SHALL NOT withdraw acceptance.

#### Scenario: Note on an unticked item
- GIVEN an accepted change with item 1.2 not ticked
- WHEN the planner runs `wm note <change> 1.2 "the parser is done; the CLI flag is not"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (note) 1.2 by <who>: the parser is done; the CLI flag is not`, and the change is still accepted

#### Scenario: Note on a ticked item
- GIVEN an accepted change with item 1.1 ticked
- WHEN the planner runs `wm note <change> 1.1 "<text>"`
- THEN it is refused, and nothing is written

### Requirement: Records written only by wm
An agent's edit to the record that adds, changes or removes a record or a tick SHALL be refused with a reason that names the `wm` command to use instead. An implementer SHALL NOT edit the record, except its resources; its notes are written with `wm note` or from its ending.

#### Scenario: Implementer writes a note by hand
- GIVEN an implementer building item 1.2
- WHEN it edits the change's task list to add a `(note)` record for item 1.2 to the Log
- THEN the edit is refused with a reason that names `wm note`

#### Scenario: Implementer edits a proposal
- GIVEN an implementer building item 1.2
- WHEN it edits the change's proposal
- THEN the edit is refused with the reason that an implementer doesn't edit the record

### Requirement: Log section
`wm` SHALL write every record of a change into a `## Log` section, the last section of the change's task list, creating the section when needed, in the order the records are written: the records about the change as a whole, `(accepted)`, `(synced)`, `(override)`, `(self-review)`, `(review)` and `(resolved)` for the review, and the records about one item. The acceptance SHALL read `<date> (accepted) fingerprint <digest> items <number>, <number>... by <who>`. The proposal SHALL hold no records, and an item SHALL hold only its definition and its tick. `wm check` SHALL report as an error, in an active change, a `## Log` section that isn't the last, or a record outside it, saying it belongs in the Log.

#### Scenario: Acceptance in the Log
- GIVEN a change whose task list has items 1.1 and 1.2 and no Log section
- WHEN the human, Ada, runs `wm accept <change>` on 2026-11-20
- THEN the task list ends with a `## Log` section holding `2026-11-20 (accepted) fingerprint <digest> items 1.1, 1.2 by Ada`, and the proposal is unchanged

#### Scenario: Record under an item
- GIVEN an active change with the line `2026-11-20 (note) by Ada: <text>` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that says records belong in the Log

# Records

## Purpose

The lines `wm` writes into a change as evidence: their one shape, where they go, and who may write them. What a human writes is a `Capital-Label:` line; what `wm` writes is a record.

## Requirements

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
`wm` SHALL write every record of a change into a `## Log` section, the last section of the change's task list, creating the section when needed, in the order the records are written: the records about the change as a whole, `(accepted)`, `(revised)`, `(synced)`, `(override)`, `(self-review)`, `(review)`, `(resolved)` for the review and `(archived)`, and the records about one item. The acceptance SHALL read `<date> (accepted) fingerprint <digest> items <number>, <number>... by <who>`. The proposal SHALL hold no records, and an item SHALL hold only its definition and its tick. `wm check` SHALL report as an error, in an active change, a `## Log` section that isn't the last, or a record outside it, saying it belongs in the Log.

#### Scenario: Acceptance in the Log
- GIVEN a change whose task list has items 1.1 and 1.2 and no Log section
- WHEN the human, Ada, runs `wm accept <change>` on 2026-11-20
- THEN the task list ends with a `## Log` section holding `2026-11-20 (accepted) fingerprint <digest> items 1.1, 1.2 by Ada`, and the proposal is unchanged

#### Scenario: Record under an item
- GIVEN an active change with the line `2026-11-20 (note) by Ada: <text>` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that says records belong in the Log

### Requirement: Findings name their place in backticks
`wm` SHALL write a finding under its review record as ``- [<severity>] `<place>`: <text>``, with the severity `critical`, `warning` or `suggestion` in brackets. The place SHALL be read whole, even when it contains a colon or `: `. In an active change, `wm check` SHALL report a finding under a review record whose severity isn't in brackets, showing the form.

#### Scenario: Place with a line number
- GIVEN a change waiting for its self-review
- WHEN the planner records it with `--finding "warning: src/a.py:12: the limit is not checked"`
- THEN the finding is written as ``- [warning] `src/a.py:12`: the limit is not checked`` under the `(self-review)` record

#### Scenario: Severity without brackets
- GIVEN an active change whose `(self-review)` record has the finding ``- warning `src/a.py:12`: the limit is not checked`` under it
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form ``- [<severity>] `<place>`: <text>``

### Requirement: Finding places relative to the project
When a finding given to `wm review` or `wm verdict` has a place that starts with an absolute path inside the project, `wm` SHALL write that path relative to the project's top folder, with forward slashes, followed by the rest of the place as given. In an atlas, a place inside a code repo registered on this machine SHALL be written as `<repo>/<path>`. A place that starts with any other absolute path SHALL be refused, before anything is written, with a reason that says to give the place relative to the project. A relative path SHALL be written with forward slashes, and a place that isn't a path SHALL be written as given.

#### Scenario: Absolute path inside the project
- GIVEN a change waiting for its self-review, in a project whose top folder is `C:\work\shop`
- WHEN the planner records it with `--finding "warning: C:\work\shop\src\limit.py:12: the limit is not checked"`
- THEN the finding is written as ``- [warning] `src/limit.py:12`: the limit is not checked``

#### Scenario: Relative path with backslashes
- GIVEN a change waiting for its self-review
- WHEN the planner records it with `--finding "suggestion: src\limit.py: name the constant"`
- THEN the finding is written as ``- [suggestion] `src/limit.py`: name the constant``

#### Scenario: Code repo of an atlas
- GIVEN an atlas whose code repo `api` is registered on this machine at `/home/sam/api`
- WHEN a reviewer's verdict is recorded with `--finding "warning: /home/sam/api/src/limit.py:12: the limit is not checked"`
- THEN the finding is written as ``- [warning] `api/src/limit.py:12`: the limit is not checked``

#### Scenario: Absolute path elsewhere
- GIVEN a change waiting for its self-review
- WHEN the planner records it with a finding whose place is an absolute path outside the project and outside every registered code repo
- THEN the review is refused with the reason that the place must be given relative to the project, and the task list is unchanged

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

### Requirement: Details under a record
`wm note`, `wm block`, `wm gap`, `wm resolve`, `wm review --self`, `wm verdict` and `wm revise` SHALL take a repeatable `--detail "<text>"`, and SHALL write each detail as a sub-bullet `  - <text>` under the record, in the order given, after its findings when it has any. The record's text SHALL still be required. A detail SHALL be one line, and SHALL NOT have a finding's shape: a severity in brackets, or a severity word followed by `:` or by a place in backticks. Other text that starts with a severity word, such as `warning signs remain`, SHALL be a detail. `wm show <change>`, in text and JSON, the implement pack's notes from earlier work, the review pack's earlier reviews and `wm pr` SHALL show each record's details under it. In an active change, `wm check` SHALL report a sub-bullet under a record of another kind as an error.

#### Scenario: Note with details
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm note <change> 1.2 "partly built" --detail "the parser is done" --detail "the CLI flag is not"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (note) 1.2 by planner for Ada: partly built`, then `  - the parser is done`, then `  - the CLI flag is not`

#### Scenario: Details in the views
- GIVEN an accepted change whose Log holds a `(note)` record for item 1.2 with the details `the parser is done` and `the CLI flag is not`
- WHEN the planner runs `wm show <change> --json`
- THEN item 1.2's note has `"details": ["the parser is done", "the CLI flag is not"]`

#### Scenario: Detail that looks like a finding
- GIVEN an accepted change with item 1.2 not ticked
- WHEN the planner runs `wm note <change> 1.2 "<text>" --detail "[warning] not a finding"`
- THEN it is refused with a reason that says a detail doesn't start with a severity in brackets, and nothing is written

#### Scenario: Detail with a finding's shape but no brackets
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --detail "warning: the retry is slow"`
- THEN it is refused with a reason that says the detail has a finding's shape, and nothing is written

#### Scenario: Detail that starts with a severity word
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --detail "warning signs remain"`
- THEN the detail is written under the `(self-review)` record, and `wm check` reports nothing about it

#### Scenario: Sub-bullet under a record without details
- GIVEN an active change whose Log holds `2026-11-20 (ticked) 1.1 by Ada` with the line `  - extra` under it
- WHEN `wm check` runs
- THEN it reports an error on that line that names the kinds of record that take details

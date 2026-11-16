# Records

## Purpose

The lines `wm` writes into a change as evidence: their one shape, where they go, who may write them, and how a record in an older format is brought to this one. What a human writes is a `Capital-Label:` line; what `wm` writes is a record.

## Requirements

### Requirement: One record shape
Every line `wm` writes as evidence SHALL be a record of the shape `(<kind>) <YYYY-MM-DD> [<args>] [by <who>]: <text>`, with the date straight after the kind, then the kind's arguments, then who wrote it. Who wrote it SHALL run to the `: ` or the end of the line, so it may hold spaces; `--by` SHALL refuse a value that holds `: `. A record with no text, such as `(reopened)`, SHALL end after who wrote it. In an active change, `wm check` SHALL report as an error a line that starts like a record and doesn't have this shape, naming the shape it expected.

#### Scenario: Blocked item
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm block <change> 1.2 "the API key is missing"` on 2026-11-20
- THEN item 1.2 has the record `(blocked) 2026-11-20 by Ada: the API key is missing` under it

#### Scenario: Malformed record
- GIVEN an active change with the line `(blocked) the API key is missing` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `(blocked) YYYY-MM-DD [by <who>]: <reason>`

### Requirement: Who wrote a record
A record SHALL name who wrote it: the git user for a command run in the session, `wm-implementer` or `wm-reviewer` for an agent's ending, or the value of `--by` when a command is given one. Every command that writes a record SHALL accept `--by <who>`. When no git user is set and no `--by` is given, the record SHALL be written without the `by` part. `wm accept` SHALL still refuse without a git user, as before.

#### Scenario: Reviewer's verdict
- GIVEN a change waiting for an independent review
- WHEN its reviewer ends with `CHANGE: <change>` and `VERDICT: pass: <reasons>` on 2026-11-20
- THEN the change's Log holds `(review) 2026-11-20 pass by wm-reviewer: <reasons>`

#### Scenario: Explicit author
- GIVEN an accepted change with every item ticked, at review level `self`
- WHEN the planner runs `wm review <change> --self "<summary>" --by "Ada and Grace"`
- THEN the self-review record reads `(self-review) <date> by Ada and Grace: <summary>`

### Requirement: Item records
`wm` SHALL write the records about one item under that item: `(blocked)` from `wm block`, `(gap)` from `wm gap`, `(note)` from `wm note`, `(reopened)` from `wm reopen` and `(resolved)` from `wm resolve <change> <item>`. An item SHALL be blocked while it has a `(blocked)` or `(gap)` record with no `(resolved)` record after it. Resolving an item SHALL add the `(resolved)` record and keep the records it resolves.

#### Scenario: Resolved item keeps its blocker
- GIVEN item 1.2 with the record `(blocked) 2026-11-20 by Ada: the API key is missing`
- WHEN the human runs `wm resolve <change> 1.2 "use the test key"` on 2026-11-21
- THEN item 1.2 holds the `(blocked)` record and, after it, `(resolved) 2026-11-21 by <who>: use the test key`, and `wm instructions` offers item 1.2 to apply

### Requirement: Notes written with wm note
`wm note <change> <item> "<text>"` SHALL write a `(note)` record under an accepted change's unticked item. It SHALL refuse an item that is already ticked, and a change that isn't accepted. A note SHALL NOT withdraw acceptance.

#### Scenario: Note on an unticked item
- GIVEN an accepted change with item 1.2 not ticked
- WHEN the planner runs `wm note <change> 1.2 "the parser is done; the CLI flag is not"`
- THEN item 1.2 has a `(note)` record with that text under it, and the change is still accepted

#### Scenario: Note on a ticked item
- GIVEN an accepted change with item 1.1 ticked
- WHEN the planner runs `wm note <change> 1.1 "<text>"`
- THEN it is refused, and nothing is written

### Requirement: Records written only by wm
An agent's edit to the record that adds, changes or removes a record or a tick SHALL be refused with a reason that names the `wm` command to use instead. An implementer SHALL NOT edit the record at all; its notes are written with `wm note` or from its ending.

#### Scenario: Implementer writes a note by hand
- GIVEN an implementer building item 1.2
- WHEN it edits the change's task list to add a note under item 1.2
- THEN the edit is refused with a reason that names `wm note`

### Requirement: Log section
`wm` SHALL write every record about a change as a whole into a `## Log` section, the last section of the change's task list, creating the section when needed: `(accepted)`, `(synced)`, `(override)`, `(self-review)`, `(review)` and `(resolved)` for the review. The acceptance SHALL read `(accepted) <date> fingerprint <digest> items <number> <number>... by <who>`. The proposal SHALL hold no records. `wm check` SHALL report as an error a `## Log` section that isn't the last, or a change-level record outside it, in an active change.

#### Scenario: Acceptance in the Log
- GIVEN a change whose task list has items 1.1 and 1.2 and no Log section
- WHEN the human, Ada, runs `wm accept <change>` on 2026-11-20
- THEN the task list ends with a `## Log` section holding `(accepted) 2026-11-20 fingerprint <digest> items 1.1 1.2 by Ada`, and the proposal is unchanged

### Requirement: Findings name their place in backticks
`wm` SHALL write a finding under its review record as `- <severity> `<place>`: <text>`, with the severity `critical`, `warning` or `suggestion`. The place SHALL be read whole, even when it contains a colon or `: `.

#### Scenario: Place with a line number
- GIVEN a change waiting for its self-review
- WHEN the planner records it with `--finding "warning: src/a.py:12: the limit is not checked"`
- THEN the finding is written as ``- warning `src/a.py:12`: the limit is not checked`` under the `(self-review)` record

### Requirement: Record format 2
This version of `wm` SHALL write and read only record format 2. `wm update` SHALL migrate every change from format 1, active and archived:
- its `Accepted:`, `Synced:` and `Review override:` lines, in the proposal or its outcome, move into the Log as `(accepted)`, `(synced)` and `(override)` records;
- an `(accepted)` record names every item of the change when the old line named none;
- its `## Review` section becomes the `## Log`, and its findings take the backticked place;
- its `Blocked:`, `Spec gap:` and `Note:` lines become `(blocked)`, `(gap)` and `(note)` records;
- a review record under an item becomes a `(note)` record that keeps its date, verdict and text, and a `review:` tag on an item is removed.

An acceptance keeps its fingerprint, so an active change accepted before the migration SHALL need to be accepted again after it. A line that had no date SHALL take the date of the last commit that touched its file, or the day of the migration when the file isn't committed.

#### Scenario: Accepted change migrated
- GIVEN a format 1 record with an accepted change whose proposal has an `Accepted:` line and whose item 1.2 has a `Blocked:` line
- WHEN `wm update` runs
- THEN the proposal has no `Accepted:` line, the task list's Log holds the `(accepted)` record, item 1.2 has a dated `(blocked)` record, `record_format` is 2, and `wm status` asks the human to accept the change again

#### Scenario: Archived change migrated
- GIVEN a format 1 record with an archived change whose task list has a `## Review` section and an item with `` `review: independent` `` and a `(review)` record under it
- WHEN `wm update` runs and then `wm show <archived change>`
- THEN its task list has a `## Log` with its review records, the item has no tag and a `(note)` record with the old review, and `wm check` reports no problem in it

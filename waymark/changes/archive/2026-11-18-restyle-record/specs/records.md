# Records

## MODIFIED Requirements

### Requirement: One record shape
Every line `wm` writes as evidence SHALL be a record of the shape `<YYYY-MM-DD> (<kind>) [<args>] [by <who>]: <text>`, with the kind straight after the date, then the kind's arguments, then who wrote it. A list of items among the arguments SHALL be separated by `, `, and a list that another argument follows SHALL end with `;`. Who wrote it SHALL run to the `: ` or the end of the line, so it may hold spaces; `--by` SHALL refuse a value that holds `: `. A record with no text, such as `(reopened)`, SHALL end after who wrote it. In an active change, `wm check` SHALL report as an error a line that starts like a record and doesn't have this shape, naming the shape it expected.

#### Scenario: Blocked item
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm block <change> 1.2 "the API key is missing"` on 2026-11-20
- THEN item 1.2 has the record `2026-11-20 (blocked) by Ada: the API key is missing` under it

#### Scenario: Malformed record
- GIVEN an active change with the line `(blocked) the API key is missing` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (blocked) [by <who>]: <reason>`

#### Scenario: Kind before the date
- GIVEN an active change with the line `(blocked) 2026-11-20 by Ada: the API key is missing` under item 1.2
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (blocked) [by <who>]: <reason>`

#### Scenario: Item list without commas
- GIVEN an active change whose Log holds `2026-11-20 (accepted) fingerprint <digest> items 1.1 1.2 by Ada`
- WHEN `wm check` runs
- THEN it reports an error on that line that names the shape `YYYY-MM-DD (accepted) fingerprint <digest> items <item>, <item>... [by <who>]`

### Requirement: Who wrote a record
A record SHALL name who wrote it: the git user for a command run in the session, `wm-implementer` or `wm-reviewer` for an agent's ending, or the value of `--by` when a command is given one. Every command that writes a record SHALL accept `--by <who>`. When no git user is set and no `--by` is given, the record SHALL be written without the `by` part. `wm accept` SHALL still refuse without a git user, as before.

#### Scenario: Reviewer's verdict
- GIVEN a change with items 1.1 and 1.2, waiting for an independent review
- WHEN its reviewer ends with `CHANGE: <change>` and `VERDICT: pass: <reasons>` on 2026-11-20
- THEN the change's Log holds `2026-11-20 (review) pass covers 1.1, 1.2 by wm-reviewer: <reasons>`

#### Scenario: Explicit author
- GIVEN an accepted change with items 1.1 and 1.2, every item ticked, at review level `self`
- WHEN the planner runs `wm review <change> --self "<summary>" --by "Ada and Grace"`
- THEN the self-review record reads `<date> (self-review) covers 1.1, 1.2 by Ada and Grace: <summary>`

### Requirement: Item records
`wm` SHALL write the records about one item under that item: `(blocked)` from `wm block`, `(gap)` from `wm gap`, `(note)` from `wm note`, `(reopened)` from `wm reopen` and `(resolved)` from `wm resolve <change> <item>`. An item SHALL be blocked while it has a `(blocked)` or `(gap)` record with no `(resolved)` record after it. Resolving an item SHALL add the `(resolved)` record and keep the records it resolves.

#### Scenario: Resolved item keeps its blocker
- GIVEN item 1.2 with the record `2026-11-20 (blocked) by Ada: the API key is missing`
- WHEN the human runs `wm resolve <change> 1.2 "use the test key"` on 2026-11-21
- THEN item 1.2 holds the `(blocked)` record and, after it, `2026-11-21 (resolved) by <who>: use the test key`, and `wm instructions` offers item 1.2 to apply

### Requirement: Log section
`wm` SHALL write every record about a change as a whole into a `## Log` section, the last section of the change's task list, creating the section when needed: `(accepted)`, `(synced)`, `(override)`, `(self-review)`, `(review)` and `(resolved)` for the review. The acceptance SHALL read `<date> (accepted) fingerprint <digest> items <number>, <number>... by <who>`. The proposal SHALL hold no records. `wm check` SHALL report as an error a `## Log` section that isn't the last, or a change-level record outside it, in an active change.

#### Scenario: Acceptance in the Log
- GIVEN a change whose task list has items 1.1 and 1.2 and no Log section
- WHEN the human, Ada, runs `wm accept <change>` on 2026-11-20
- THEN the task list ends with a `## Log` section holding `2026-11-20 (accepted) fingerprint <digest> items 1.1, 1.2 by Ada`, and the proposal is unchanged

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

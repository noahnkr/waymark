# Formatting

## Purpose

How `wm check --fix` brings the record to its standard layout when the human asks: what it rewrites, what it never touches, and what it reports.

## Requirements

### Requirement: Fix the layout on request
`wm check --fix` SHALL rewrite the record into its standard layout, then report what the check still finds. It SHALL rewrite:
- the records `wm` owns into their standard shape, when the kind, date and text can be read unambiguously;
- a label written plain, `- <Label>:` or `- **<Label>**:`, into its bold form `- **<Label>:**`, for the labels the record reads;
- a charter glossary entry written `- <term>: <meaning>` or `- **<term>**: <meaning>` into `- **<term>:** <meaning>`;
- a task item's label lines into the order Build, Repo, Criteria, Verify, each keeping the lines nested under it;
- list markers `*` and `+` into `-`;
- one blank line before each heading, and at most one after it, so a heading such as `### Requirement:` may keep its text directly underneath;
- trailing spaces off every line;
- the end of each file to exactly one line break.

It SHALL keep each file's line endings, and SHALL NOT change wording, fenced code, comments or links. It SHALL cover the charter, the specs, the active changes, the explorations, the milestones and the resources, and SHALL NOT touch archived changes.

#### Scenario: Layout fixed
- GIVEN an active change whose proposal uses `*` list markers and has trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the proposal uses `-` markers with no trailing spaces, its wording is unchanged, and the output names the proposal as fixed

#### Scenario: Fenced code left alone
- GIVEN a design with a fenced code block holding `* item  ` with trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the fenced block is unchanged

#### Scenario: Plain label made bold
- GIVEN an active change whose proposal has the line `- Owner: Ada`
- WHEN the human runs `wm check --fix`
- THEN the line reads `- **Owner:** Ada`, and the output names the proposal as fixed

#### Scenario: Glossary entry made bold
- GIVEN a charter whose glossary has the lines `- Record: everything in waymark/` and `- **Atlas**: a separate repository`
- WHEN the human runs `wm check --fix`
- THEN they read `- **Record:** everything in waymark/` and `- **Atlas:** a separate repository`, and the output names the charter as fixed

#### Scenario: Item lines put in order
- GIVEN an active change whose item 1.2 has `- **Criteria:**` with two bullets under it, then `- **Verify:** wm check`, then `- **Build:** delegate`
- WHEN the human runs `wm check --fix`
- THEN item 1.2's lines are `- **Build:** delegate`, then the Criteria line with its two bullets, then the Verify line, and the output names the task list as fixed

### Requirement: Report what was fixed
`wm check --fix` SHALL name each file it rewrote and the kinds of fix it made there, and SHALL say so when there was nothing to fix. Its result SHALL be that of `wm check` on the fixed record: it fails when an error remains.

#### Scenario: Nothing to fix
- GIVEN a record in its standard layout with no errors
- WHEN the human runs `wm check --fix`
- THEN it says there was nothing to fix and that the record is healthy, and no file is written

#### Scenario: Error that can't be fixed
- GIVEN an active change whose proposal links to a file that doesn't exist
- WHEN the human runs `wm check --fix`
- THEN the link is not changed, and the check fails with the broken link

### Requirement: Fix keeps acceptance
A fix SHALL NOT withdraw the acceptance of any change, and SHALL NOT add, change the meaning of, or remove any record or tick.

#### Scenario: Accepted change fixed
- GIVEN an accepted change whose design has trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the design has no trailing spaces, and the change is still accepted

### Requirement: Fix refused when the record can't be written
`wm check --fix` SHALL be refused, writing nothing, when writing commands are refused: when this `wm` isn't the version the project is pinned to, or when the record is in another format, in which case the reason SHALL be the one the requirement "Record format 1" gives. The fix SHALL write every file or none.

#### Scenario: Record in another format
- GIVEN a record at format 3, pinned to the running `wm`
- WHEN the human runs `wm check --fix`
- THEN it is refused with a reason that says to install the `wm` version that wrote the record, and no file is written

# Formatting

## Purpose

How `wm check --fix` brings the record to its standard layout when the human asks: what it rewrites, what it never touches, and what it reports.

## Requirements

### Requirement: Fix the layout on request
`wm check --fix` SHALL rewrite the record into its standard layout, then report what the check still finds. It SHALL rewrite:
- the records `wm` owns into their standard shape, when the kind, date and text can be read unambiguously;
- list markers `*` and `+` into `-`;
- one blank line before each heading, and at most one after it, so a heading such as `### Requirement:` may keep its text directly underneath;
- trailing spaces off every line;
- the end of each file to exactly one line break.

It SHALL keep each file's line endings, and SHALL NOT change wording, fenced code, comments or links. It SHALL cover the charter, the specs, the active changes, the explorations and the milestones, and SHALL NOT touch archived changes.

#### Scenario: Layout fixed
- GIVEN an active change whose proposal uses `*` list markers and has trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the proposal uses `-` markers with no trailing spaces, its wording is unchanged, and the output names the proposal as fixed

#### Scenario: Fenced code left alone
- GIVEN a design with a fenced code block holding `* item  ` with trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the fenced block is unchanged

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
`wm check --fix` SHALL be refused, writing nothing, when writing commands are refused: when this `wm` isn't the version the project is pinned to, or when the record is in an older format, in which case the reason SHALL name `wm update`. The fix SHALL write every file or none.

#### Scenario: Older record format
- GIVEN a record in format 1
- WHEN the human runs `wm check --fix`
- THEN it is refused with a reason that says to run `wm update` first, and no file is written

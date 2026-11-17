# Formatting

## MODIFIED Requirements

### Requirement: Fix refused when the record can't be written
`wm check --fix` SHALL be refused, writing nothing, when writing commands are refused: when this `wm` isn't the version the project is pinned to, or when the record is in another format, in which case the reason SHALL be the one the requirement "Record format 1" gives. The fix SHALL write every file or none.

#### Scenario: Record in another format
- GIVEN a record at format 3, pinned to the running `wm`
- WHEN the human runs `wm check --fix`
- THEN it is refused with a reason that says to install the `wm` version that wrote the record, and no file is written

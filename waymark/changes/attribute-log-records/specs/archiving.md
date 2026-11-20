# Archiving

## ADDED Requirements

### Requirement: Archive recorded in the Log
`wm archive` SHALL write `<date> (archived) by <who>` at the end of the change's Log, naming the human who archived it, before it moves the change to the archive. An archive that is refused SHALL write nothing.

#### Scenario: Archived change
- GIVEN an applied and reviewed change, and a git user named Ada
- WHEN Ada runs `wm archive <change> --built "<text>"` on 2026-11-21
- THEN the archived change's Log ends with `2026-11-21 (archived) by Ada`

#### Scenario: Refused archive
- GIVEN a change that needs a review and has no passing one
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the change's Log has no `(archived)` record

# Records

## MODIFIED Requirements

### Requirement: Records written only by wm
An agent's edit to the record that adds, changes or removes a record or a tick SHALL be refused with a reason that names the `wm` command to use instead. An implementer SHALL NOT edit the record, except its resources; its notes are written with `wm note` or from its ending.

#### Scenario: Implementer writes a note by hand
- GIVEN an implementer building item 1.2
- WHEN it edits the change's task list to add a note under item 1.2
- THEN the edit is refused with a reason that names `wm note`

#### Scenario: Implementer edits a proposal
- GIVEN an implementer building item 1.2
- WHEN it edits the change's proposal
- THEN the edit is refused with the reason that an implementer doesn't edit the record

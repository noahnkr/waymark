# Setup

## MODIFIED Requirements

### Requirement: Record folders kept in git
`wm init`, when it creates a record, SHALL write an empty `.gitkeep` file into each of the record's folders: `specs/`, `changes/`, `changes/archive/`, `explorations/`, `milestones/`, `milestones/archive/` and `resources/`. `wm update` SHALL write the `.gitkeep` missing from any of these folders, list each as created, and tell the user to review and commit the record. No `wm` command SHALL remove a `.gitkeep`, and `wm check` SHALL NOT report one.

#### Scenario: New record
- GIVEN a git repository with no record
- WHEN `wm init` runs
- THEN each of the seven folders holds an empty `.gitkeep`, and after committing `waymark/`, a fresh clone has all seven folders

#### Scenario: Existing record without them
- GIVEN a project at the pinned version whose record has no `.gitkeep` files and no `changes/archive/` folder
- WHEN `wm update` runs
- THEN all seven folders hold an empty `.gitkeep`, the output lists each as `created: waymark/<folder>/.gitkeep`, and its last line asks to review the changes to `waymark/` and commit them

#### Scenario: Record without resources
- GIVEN a project at the pinned version whose record has the six other folders, each with a `.gitkeep`, and no `resources/` folder
- WHEN `wm update` runs
- THEN `resources/.gitkeep` exists, and the output lists `created: waymark/resources/.gitkeep` and no other `.gitkeep`

#### Scenario: Already in place
- GIVEN a record whose seven folders each hold a `.gitkeep`
- WHEN `wm update` runs
- THEN no `.gitkeep` is written, and the output doesn't mention them

#### Scenario: Last change archived
- GIVEN a record with one active change, whose folder `changes/` also holds a `.gitkeep`
- WHEN the change is archived
- THEN `changes/.gitkeep` is still there, and `wm check` reports nothing about it

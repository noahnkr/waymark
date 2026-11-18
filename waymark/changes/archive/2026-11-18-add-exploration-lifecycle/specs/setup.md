# Setup

## MODIFIED Requirements

### Requirement: Record folders kept in git
`wm init`, when it creates a record, SHALL write an empty `.gitkeep` file into each of the record's folders: `specs/`, `changes/`, `changes/archive/`, `explorations/`, `explorations/archive/`, `milestones/`, `milestones/archive/` and `resources/`. `wm update` SHALL write the `.gitkeep` missing from any of these folders, list each as created, and tell the user to review and commit the record. No `wm` command SHALL remove a `.gitkeep`, and `wm check` SHALL NOT report one.

#### Scenario: New record
- GIVEN a git repository with no record
- WHEN `wm init` runs
- THEN each of the eight folders holds an empty `.gitkeep`, and after committing `waymark/`, a fresh clone has all eight folders

#### Scenario: Existing record without them
- GIVEN a project at the pinned version whose record has no `.gitkeep` files and no `changes/archive/` folder
- WHEN `wm update` runs
- THEN all eight folders hold an empty `.gitkeep`, the output lists each as `created: waymark/<folder>/.gitkeep`, and its last line asks to review the changes to `waymark/` and commit them

#### Scenario: Record without resources
- GIVEN a project at the pinned version whose record has the seven other folders, each with a `.gitkeep`, and no `resources/` folder
- WHEN `wm update` runs
- THEN `resources/.gitkeep` exists, and the output lists `created: waymark/resources/.gitkeep` and no other `.gitkeep`

#### Scenario: Record without an explorations archive
- GIVEN a project at the pinned version whose record has the seven other folders, each with a `.gitkeep`, and no `explorations/archive/` folder
- WHEN `wm update` runs
- THEN `explorations/archive/.gitkeep` exists, and the output lists `created: waymark/explorations/archive/.gitkeep` and no other `.gitkeep`

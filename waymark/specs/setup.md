# Setup

## Purpose

How `wm` sets up a repository on one machine: the agent tool files, which belong to the machine, and how they are kept out of git. The record itself is shared and committed.

## Requirements

### Requirement: Machine setup in a clone
In a git repository that already has a record, `wm init` SHALL set up this machine without changing the record. It SHALL write the agent tool files for the tools the settings list and add the ignore block. It SHALL NOT write git hooks or change git's settings.

#### Scenario: Fresh clone
- GIVEN a clone of a project whose record is committed and whose agent tool files are not
- WHEN `wm init` runs with the pinned version of `wm`
- THEN the agent tool files are written, the ignore block is in `.gitignore`, no git setting has changed, and no file under `waymark/` has changed

#### Scenario: Run again
- GIVEN a clone where `wm init` has already set up this machine
- WHEN `wm init` runs again
- THEN no file changes, and it says the machine is already set up

#### Scenario: Other version
- GIVEN a project pinned to a `wm` version other than the one running
- WHEN `wm init` runs
- THEN it is refused, nothing is written, and the message gives the command that installs the pinned version

#### Scenario: Record in another format
- GIVEN a project whose record is in a format other than the one the running `wm` reads
- WHEN `wm init` runs
- THEN it is refused, nothing is written, and the message says to install the `wm` version that wrote the record

### Requirement: Machine files ignored
`wm init` and `wm update` SHALL keep the files `wm` writes for a machine out of git through one marked block in the repository's top `.gitignore`, listing the shared skills `wm` writes and each listed agent tool's files. The block SHALL NOT list `waymark/`, and lines outside the block SHALL be kept byte for byte.

#### Scenario: New project
- GIVEN a git repository with no `.gitignore`
- WHEN `wm init` creates the record
- THEN `.gitignore` holds the block, and `git status` shows only `waymark/` and `.gitignore` as new

#### Scenario: Existing ignore file
- GIVEN a `.gitignore` with the project's own lines and no block
- WHEN `wm init` runs
- THEN the block is added at the end, and the project's own lines are unchanged

#### Scenario: Block already current
- GIVEN a `.gitignore` whose block lists what `wm` would write
- WHEN `wm update` runs
- THEN `.gitignore` is not changed

#### Scenario: Block out of date
- GIVEN a `.gitignore` whose block lists other paths than `wm` would write, such as the git hooks a 0.1.1 block listed
- WHEN `wm update` runs
- THEN the block is replaced with the current list, in place, and the lines around it are unchanged

### Requirement: Tracked machine files reported
`wm doctor` SHALL warn when a file `wm` writes for a machine is tracked in git, and the warning SHALL give the `git rm -r --cached` command that stops tracking those files without deleting them.

#### Scenario: Agent files committed
- GIVEN a project whose `.claude/` files were committed
- WHEN `wm doctor` runs
- THEN it warns, names the tracked paths, and gives one `git rm -r --cached` command for them

#### Scenario: Nothing tracked
- GIVEN a project set up by `wm init` with the block in place
- WHEN `wm doctor` runs
- THEN the check passes

### Requirement: Setup messages
Messages about the agent tool files SHALL tell the user to run `wm init` to set up or refresh them, and SHALL NOT tell them to commit them. `wm update` SHALL still tell the user to review and commit the changes it made to the record and to `.gitignore`.

#### Scenario: Agent files out of date
- GIVEN a project whose agent tool files are missing on this machine
- WHEN `wm doctor` runs
- THEN the warning says to run `wm init`, and does not say to commit

#### Scenario: Update changes only machine files
- GIVEN a project where `wm update` rewrites only agent tool files
- WHEN it finishes
- THEN its output does not tell the user to commit anything

### Requirement: Retired skills removed
`wm init` and `wm update` SHALL remove every skill folder whose name starts with `wm-` and that the running `wm` doesn't ship, from the shared skills folder and from each listed agent tool's skills folder, and SHALL list each removed file as removed. Folders whose names don't start with `wm-` SHALL be left as they are.

#### Scenario: Skill retired
- GIVEN a machine set up by a `wm` that shipped `wm-fix`, with `wm-fix` in the shared skills folder and in Claude Code's
- WHEN `wm update` runs
- THEN both `wm-fix` folders are gone, and the output lists their files as removed

#### Scenario: The project's own skill
- GIVEN a Claude Code skills folder holding a skill named `release-notes` that `wm` didn't write
- WHEN `wm init` runs
- THEN the `release-notes` folder is unchanged

### Requirement: Record folders kept in git
`wm init`, when it creates a record, SHALL write an empty `.gitkeep` file into each of the record's folders: `specs/`, `changes/`, `changes/archive/`, `explorations/`, `milestones/` and `milestones/archive/`. `wm update` SHALL write the `.gitkeep` missing from any of these folders, list each as created, and tell the user to review and commit the record. No `wm` command SHALL remove a `.gitkeep`, and `wm check` SHALL NOT report one.

#### Scenario: New record
- GIVEN a git repository with no record
- WHEN `wm init` runs
- THEN each of the six folders holds an empty `.gitkeep`, and after committing `waymark/`, a fresh clone has all six folders

#### Scenario: Existing record without them
- GIVEN a project at the pinned version whose record has no `.gitkeep` files and no `changes/archive/` folder
- WHEN `wm update` runs
- THEN all six folders hold an empty `.gitkeep`, the output lists each as `created: waymark/<folder>/.gitkeep`, and its last line asks to review the changes to `waymark/` and commit them

#### Scenario: Already in place
- GIVEN a record whose six folders each hold a `.gitkeep`
- WHEN `wm update` runs
- THEN no `.gitkeep` is written, and the output doesn't mention them

#### Scenario: Last change archived
- GIVEN a record with one active change, whose folder `changes/` also holds a `.gitkeep`
- WHEN the change is archived
- THEN `changes/.gitkeep` is still there, and `wm check` reports nothing about it

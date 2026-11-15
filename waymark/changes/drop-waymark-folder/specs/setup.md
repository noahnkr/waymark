# Setup

## Purpose

How `wm` sets up a repository on one machine: the agent tool files, which belong to the machine, and how they are kept out of git. The record itself is shared and committed.

## Added requirements

### Requirement: Old git hooks removed
`wm init` and `wm update` SHALL remove the git hooks that `wm` 0.1.1 installed: when this clone's `core.hooksPath` is `.waymark/hooks`, they SHALL unset it and delete `.waymark/hooks/`. They SHALL leave any other `core.hooksPath` and any other hooks alone.

#### Scenario: Clone set up by 0.1.1
- GIVEN a clone whose `core.hooksPath` is `.waymark/hooks` and whose `.waymark/hooks/` holds the two hooks
- WHEN `wm update` runs
- THEN `core.hooksPath` is unset, `.waymark/hooks/` is gone, and the output says the git hooks were removed

#### Scenario: Another hook setup
- GIVEN a clone whose `core.hooksPath` is `.husky`
- WHEN `wm init` runs
- THEN `core.hooksPath` is still `.husky`, and nothing in `.husky/` has changed

## Modified requirements

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

#### Scenario: Record needs migrating
- GIVEN a project whose record format is older than the running `wm` writes
- WHEN `wm init` runs
- THEN it is refused, nothing is written, and the message says to run `wm update`

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
`wm doctor` SHALL warn when a file `wm` writes for a machine, or a git hook `wm` 0.1.0 committed under `.waymark/hooks/`, is tracked in git, and the warning SHALL give the `git rm -r --cached` command that stops tracking those files without deleting them.

#### Scenario: Project set up with 0.1.0
- GIVEN a project whose `.claude/` files and `.waymark/hooks/` were committed
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

## Removed requirements

### Requirement: Git hooks not staged
Reason: `wm` no longer installs git hooks. Commit messages are checked by the agent's command hook, and `wm check` runs in CI.

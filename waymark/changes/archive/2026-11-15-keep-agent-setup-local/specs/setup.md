# Setup

## Purpose

How `wm` sets up a repository on one machine: the agent tool files and the git hooks, which belong to the machine, and how they are kept out of git. The record itself is shared and committed.

## ADDED Requirements

### Requirement: Machine setup in a clone
In a git repository that already has a record, `wm init` SHALL set up this machine without changing the record. It SHALL write the agent tool files for the tools the settings list, install the git hooks, and add the ignore block.

#### Scenario: Fresh clone
- GIVEN a clone of a project whose record is committed and whose agent tool files and git hooks are not
- WHEN `wm init` runs with the pinned version of `wm`
- THEN the agent tool files and the git hooks are written, `core.hooksPath` points at the hooks, the ignore block is in `.gitignore`, and no file under `waymark/` has changed

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
`wm init`, `wm update` and `wm git-hooks` SHALL keep the files `wm` writes for a machine out of git through one marked block in the repository's top `.gitignore`. Where the repository has a record, the block SHALL list the shared skills `wm` writes, each listed agent tool's files and the git hooks. Elsewhere it SHALL list only the git hooks. The block SHALL NOT list `waymark/` or the atlas pointer, and lines outside the block SHALL be kept byte for byte.

#### Scenario: New project
- GIVEN a git repository with no `.gitignore`
- WHEN `wm init` creates the record
- THEN `.gitignore` holds the block, `git status` shows `waymark/` and `.gitignore` as new, and shows no agent tool file or git hook

#### Scenario: Existing ignore file
- GIVEN a `.gitignore` with the project's own lines and no block
- WHEN `wm init` runs
- THEN the block is added at the end, and the project's own lines are unchanged

#### Scenario: Block already current
- GIVEN a `.gitignore` whose block lists what `wm` would write
- WHEN `wm update` runs
- THEN `.gitignore` is not changed

#### Scenario: Block out of date
- GIVEN a `.gitignore` whose block lists other paths than `wm` would write, such as after a tool is added to the settings
- WHEN `wm update` runs
- THEN the block is replaced with the current list, in place, and the lines around it are unchanged

#### Scenario: Code repo with git hooks only
- GIVEN a code repo of an atlas, with no record
- WHEN `wm git-hooks` runs in it
- THEN its `.gitignore` block lists only the git hooks, and `.waymark/atlas.toml` is not ignored

### Requirement: Git hooks not staged
Installing the git hooks SHALL write them, make them executable and point this clone's `core.hooksPath` at them, and SHALL NOT stage them or tell the user to commit them.

#### Scenario: Install the hooks
- GIVEN a git repository without the hooks
- WHEN `wm git-hooks` runs
- THEN the hooks are written and executable, `core.hooksPath` is `.waymark/hooks`, nothing is staged, and the output does not mention committing them

#### Scenario: Hooks run after a clone
- GIVEN a fresh clone of a project, after `wm init`
- WHEN a commit is made with the message `wip`
- THEN the commit-msg hook refuses it

### Requirement: Tracked machine files reported
`wm doctor` SHALL warn when a file `wm` writes for a machine is tracked in git, and the warning SHALL give the `git rm -r --cached` command that stops tracking those files without deleting them.

#### Scenario: Project set up with 0.1.0
- GIVEN a project whose `.claude/` files and `.waymark/hooks/` were committed
- WHEN `wm doctor` runs
- THEN it warns, names the tracked paths, and gives one `git rm -r --cached` command for them

#### Scenario: Nothing tracked
- GIVEN a project set up by `wm init` with the block in place
- WHEN `wm doctor` runs
- THEN the check passes

### Requirement: Setup messages
Messages about the agent tool files and the git hooks SHALL tell the user to run `wm init` to set up or refresh them, and SHALL NOT tell them to commit them. `wm update` SHALL still tell the user to review and commit the changes it made to the record and to `.gitignore`.

#### Scenario: Agent files out of date
- GIVEN a project whose agent tool files are missing on this machine
- WHEN `wm doctor` runs
- THEN the warning says to run `wm init`, and does not say to commit

#### Scenario: Update changes only machine files
- GIVEN a project where `wm update` rewrites only agent tool files
- WHEN it finishes
- THEN its output does not tell the user to commit anything

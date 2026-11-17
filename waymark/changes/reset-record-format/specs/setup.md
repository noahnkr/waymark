# Setup

## MODIFIED Requirements

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

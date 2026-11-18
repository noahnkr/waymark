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

### Requirement: Interactive init
When both its input and its output are a terminal, and it is given none of `--atlas`, `--tool` or `--yes`, `wm init` in a repository with no record SHALL show a welcome screen and wait for Enter, then ask whether the repository is a project or an atlas, and for an atlas its name; which agent tools to set up; and whether to add the CI workflow. It SHALL then write exactly what `wm init` writes given the same answers as flags, plus the CI workflow when asked for it, and print what it created and the next step. The welcome screen SHALL show the Waymark star, the name, the tagline "Leave a trail your agents can follow.", what `wm init` sets up, and the skills to run next.

#### Scenario: Project with Claude Code and CI
- GIVEN a git repository with no record, `wm init` run on a terminal
- WHEN the human presses Enter at the welcome screen, chooses a project, keeps Claude Code selected and answers yes to the CI workflow
- THEN the record, the Claude Code files and `.github/workflows/waymark.yml` are written, and the output lists them and ends with the next step

#### Scenario: Atlas
- GIVEN a git repository with no record, `wm init` run on a terminal
- WHEN the human chooses an atlas and enters the name `shop-platform`
- THEN the settings written are those of `wm init --atlas shop-platform`

#### Scenario: Invalid atlas name
- GIVEN `wm init` run on a terminal, at the atlas name
- WHEN the human enters `shop platform`
- THEN the question stays open with the reason the name can't be used, and nothing is written

### Requirement: Agent tools to choose from
The interactive tool question SHALL list every agent tool `wm` has an adapter for. A tool whose files or folder are found in the repository SHALL be selected to start with; when none is found, every tool SHALL be. Confirming with no tool selected SHALL be refused with a reason, and the question SHALL stay open.

#### Scenario: Tool detected
- GIVEN a repository with a `.claude/` folder and no record, `wm init` run on a terminal
- WHEN the tool question is shown
- THEN Claude Code is listed, selected, and marked as found

#### Scenario: Nothing selected
- GIVEN the tool question with every tool unselected
- WHEN the human presses Enter
- THEN the question stays open with the reason that at least one tool is needed

### Requirement: Canceled init writes nothing
Pressing Esc or Ctrl+C at the welcome screen or at any question SHALL end `wm init` with nothing written, print `Setup canceled. Nothing was written.`, and exit with a non-zero status.

#### Scenario: Canceled at the tools
- GIVEN `wm init` run on a terminal, at the tool question
- WHEN the human presses Esc
- THEN no file in the repository is created or changed, and the output ends with `Setup canceled. Nothing was written.`

### Requirement: Init without questions
`wm init` SHALL ask nothing, and SHALL do what it did before this requirement, when its input or its output isn't a terminal, or when it is given `--atlas`, `--tool` or `--yes`. In a clone that already has a record, `wm init` SHALL ask nothing; on a terminal it SHALL show the welcome screen first, and then set up the machine from the record's settings.

#### Scenario: Run by an agent
- GIVEN a git repository with no record
- WHEN an agent runs `wm init` with its output piped
- THEN no welcome screen or question is shown, and the record and every agent tool's files are written as before

#### Scenario: Yes flag on a terminal
- GIVEN a git repository with no record
- WHEN the human runs `wm init --yes` on a terminal
- THEN no welcome screen or question is shown, and the result is what `wm init` wrote before

#### Scenario: Clone on a terminal
- GIVEN a clone with a record and no agent tool files on this machine
- WHEN the human runs `wm init` on a terminal and presses Enter at the welcome screen
- THEN the machine is set up from `agent_tools`, no question is asked, and the record is unchanged

### Requirement: Questions without raw mode
When the terminal can't be put into raw mode, the interactive `wm init` SHALL ask the same questions as numbered choices typed at a line, with the same defaults, and SHALL show the welcome screen without animation.

#### Scenario: Numbered choices
- GIVEN a terminal that can't be put into raw mode
- WHEN the human runs `wm init` and types `2` at the repository question
- THEN the next question asks for the atlas's name

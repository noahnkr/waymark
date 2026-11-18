# Setup

## ADDED Requirements

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

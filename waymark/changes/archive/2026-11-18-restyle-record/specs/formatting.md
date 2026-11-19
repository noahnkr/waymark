# Formatting

## MODIFIED Requirements

### Requirement: Fix the layout on request
`wm check --fix` SHALL rewrite the record into its standard layout, then report what the check still finds. It SHALL rewrite:
- the records `wm` owns into their standard shape, when the kind, date and text can be read unambiguously;
- a label written plain, `- <Label>:` or `- **<Label>**:`, into its bold form `- **<Label>:**`, for the labels the record reads;
- a task item's label lines into the order Build, Repo, Criteria, Verify, each keeping the lines nested under it;
- list markers `*` and `+` into `-`;
- one blank line before each heading, and at most one after it, so a heading such as `### Requirement:` may keep its text directly underneath;
- trailing spaces off every line;
- the end of each file to exactly one line break.

It SHALL keep each file's line endings, and SHALL NOT change wording, fenced code, comments or links. It SHALL cover the charter, the specs, the active changes, the explorations, the milestones and the resources, and SHALL NOT touch archived changes.

#### Scenario: Layout fixed
- GIVEN an active change whose proposal uses `*` list markers and has trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the proposal uses `-` markers with no trailing spaces, its wording is unchanged, and the output names the proposal as fixed

#### Scenario: Fenced code left alone
- GIVEN a design with a fenced code block holding `* item  ` with trailing spaces
- WHEN the human runs `wm check --fix`
- THEN the fenced block is unchanged

#### Scenario: Plain label made bold
- GIVEN an active change whose proposal has the line `- Owner: Ada`
- WHEN the human runs `wm check --fix`
- THEN the line reads `- **Owner:** Ada`, and the output names the proposal as fixed

#### Scenario: Item lines put in order
- GIVEN an active change whose item 1.2 has `- **Criteria:**` with two bullets under it, then `- **Verify:** wm check`, then `- **Build:** delegate`
- WHEN the human runs `wm check --fix`
- THEN item 1.2's lines are `- **Build:** delegate`, then the Criteria line with its two bullets, then the Verify line, and the output names the task list as fixed

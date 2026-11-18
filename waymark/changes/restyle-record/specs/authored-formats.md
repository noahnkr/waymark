# Authored formats

## ADDED Requirements

### Requirement: Labels in bold
Every label line in the record SHALL be written with the label in bold and the colon inside it, `**<Label>:** <text>`, as a bullet `- **<Label>:** <text>` wherever the label is a list line. The labels SHALL be: a proposal's facts (`Owner`, `Milestone`, `After`, `Review`, `Path`); its Impact (`Specs`, `User-visible`, `Code`) and Outcome (`Built`, `Differs`); a task item's `Build`, `Repo`, `Criteria` and `Verify`; a design decision's `Status`, `Decided by`, `Options`, `Choice` and `Why`; a delta's `From`, `To` and `Reason`, and a spec's or delta's `Repos`; an exploration's `Status`; and a resource's `Kind`, `Serves`, `Status` and `Verified`. `wm` SHALL write the label lines it writes in this form. A label written plain SHALL NOT be read as the label, and `wm check` SHALL report one, `- <Label>:` or `- **<Label>**:`, in the charter, a spec, an active change, an exploration or a resource as an error that shows the bold form.

#### Scenario: New change
- GIVEN a project with git user Ada
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- **Owner:** Ada` and `- **Path:** short` under its title

#### Scenario: Plain label
- GIVEN an active change whose item 1.2 has the line `- Criteria: fifty at most` and no other Criteria line
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form `- **Criteria:**`

#### Scenario: Colon outside the bold
- GIVEN a resource with the line `- **Kind**: service`
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form `- **Kind:**`

### Requirement: Item lines in order
A task item's label lines SHALL come in the order `Build`, `Repo`, `Criteria`, `Verify`, before any record under the item; `Repo` MAY be left out. `wm check` SHALL report as an error, in an active change, an item whose label lines are in another order, naming the order.

#### Scenario: Build line last
- GIVEN an active change whose item 1.2 has its `- **Criteria:**` and `- **Verify:**` lines, then `- **Build:** delegate`
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names the order Build, Repo, Criteria, Verify

#### Scenario: Lines in order
- GIVEN an active change whose item 1.2 has `- **Build:** planner`, `- **Criteria:**` with two bullets, and `- **Verify:**`, in that order
- WHEN `wm check` runs
- THEN it reports no problem on item 1.2

## MODIFIED Requirements

### Requirement: Proposal facts as a list
A proposal's facts SHALL be bullet lines between its title and its first section: `- **Owner:** <name>`, and optionally `- **Milestone:** <name>`, `- **After:** <change>`, `- **Review:** <level>` and `- **Path:** short`. `wm new change` SHALL write them so. A fact written without the bullet SHALL NOT be read as a fact.

#### Scenario: New change
- GIVEN a project with git user Ada
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- **Owner:** Ada` and `- **Path:** short` under its title

#### Scenario: Fact without a bullet
- GIVEN an active change whose proposal has the line `**Owner:** Ada` without a bullet, and no `- **Owner:**` line
- WHEN `wm check` runs
- THEN it reports that the proposal has no owner, and no message names `wm update`

### Requirement: Glossary as a list
The charter's glossary SHALL be a list of `- **<term>:** <meaning>` lines, the colon inside the bold. `wm check` SHALL report a glossary line in another form as an error that shows the form.

#### Scenario: Old glossary line
- GIVEN a charter whose glossary has the line `Record: everything in waymark/`
- WHEN `wm check` runs
- THEN it reports an error that shows the form `- **<term>:** <meaning>`

#### Scenario: Colon outside the bold
- GIVEN a charter whose glossary has the line `- **Record**: everything in waymark/`
- WHEN `wm check` runs
- THEN it reports an error that shows the form `- **<term>:** <meaning>`

### Requirement: Criteria and verification as nested lists
A task item's `- **Criteria:**` and `- **Verify:**` lines MAY each be followed by a nested list, one criterion or one verification step per bullet, indented under it. The item's criteria SHALL be the Criteria line's own text and every bullet under it, in order, and its verification SHALL be the Verify line's own text and every bullet under it, in order. Both SHALL be part of the definition the human accepts.

#### Scenario: Nested criteria
- GIVEN an item with `- **Criteria:**` and, under it, the bullets `fifty at most` and `sorted by score`
- WHEN the planner runs `wm context <change> <item> --for implement`
- THEN the item's criteria in the pack list both bullets

#### Scenario: Nested verification
- GIVEN an item with `- **Verify:**` and, under it, the bullets `a test for the limit` and `wm check here`
- WHEN the planner runs `wm context <change> <item> --for implement`
- THEN the item's verification in the pack lists both bullets

### Requirement: Delta sections
A delta's sections SHALL be `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements`. Under RENAMED, each rename SHALL be a `- **From:** <old name>` line followed by a `- **To:** <new name>` line. Archiving or syncing the change SHALL rename the requirement in the spec and keep its statement and scenarios. A rename whose old name the spec doesn't have, or whose new name it already has, SHALL be a conflict. `wm check` SHALL report a section heading that matches one of these in another case, showing the heading it expects.

#### Scenario: Requirement renamed
- GIVEN a spec with the requirement "Result cap"
- WHEN a change whose delta renames "Result cap" to "Result limit" is archived
- THEN the spec has the requirement "Result limit" with the same statement and scenarios, and no "Result cap"

#### Scenario: Rename of a missing requirement
- GIVEN a spec without the requirement "Result cap"
- WHEN a change's delta renames "Result cap" to "Result limit"
- THEN `wm check` reports a conflict on that delta

#### Scenario: Heading in another case
- GIVEN an active change whose delta has the heading `## Added Requirements`
- WHEN `wm check` runs
- THEN it reports an error on that heading that shows `## ADDED Requirements`, and no message names `wm update`

### Requirement: Structured impact
A proposal's `## Impact` section SHALL hold a `- **Specs:**` line, a `- **User-visible:**` line and a `- **Code:**` line, each followed by text or by nested bullets. The Specs line SHALL name each spec the change has a delta for, in backticks, or say `none`. `wm check` SHALL report a missing line, a spec named on the Specs line that has no delta in the change, and a delta whose spec isn't named.

#### Scenario: Impact matches the deltas
- GIVEN an active change with a delta for `search` and the line `- **Specs:** `search` (modified)`
- WHEN `wm check` runs
- THEN it reports no problem in the Impact

#### Scenario: Delta not named in the impact
- GIVEN an active change with deltas for `search` and `ranking` and the line `- **Specs:** `search` (modified)`
- WHEN `wm check` runs
- THEN it reports an error on the proposal that names `ranking`

### Requirement: Structured outcome
`wm archive` SHALL take `--built` and `--differs` instead of `--outcome`, and SHALL write them as `- **Built:** <text>` and `- **Differs:** <text>` lines under the archived proposal's `## Outcome`. `--differs` MAY be left out, and SHALL then be written as `none`. `wm pr` SHALL show both lines.

#### Scenario: Archived with an outcome
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has the lines `- **Built:** The result limit.` and `- **Differs:** Fifty, not twenty.`

#### Scenario: Nothing differs
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit."`
- THEN the archived proposal's Outcome has the line `- **Differs:** none`

### Requirement: Settled decisions
Each `### Decision:` in a design SHALL have a `- **Status:**` line, `proposed` or `decided`, and a `- **Decided by:**` line, `human` or `planner`. A design SHALL have an `## Open questions` section, holding a list of questions or the word `None.`. `wm check` SHALL report a missing or unknown value. `wm accept` SHALL refuse a change while a decision is `proposed` or an open question is listed, naming each one.

#### Scenario: Proposed decision
- GIVEN a change whose design has a decision with `- **Status:** proposed`
- WHEN the human runs `wm accept <change>`
- THEN it is refused with a reason that names the decision, and the change is not accepted

#### Scenario: Open question
- GIVEN a change whose design lists the open question "Fifty or twenty?"
- WHEN the human runs `wm accept <change>`
- THEN it is refused with a reason that names the question

### Requirement: New work only
`wm check` SHALL hold active changes, the charter and explorations to the layouts of the requirements "Structured impact", "Numbered goals and constraints", "Settled decisions", "Items say how they are done", "Item lines in order" and "Decisions weigh options". An archived change SHALL be read as it was written, and SHALL NOT be reported for them.

#### Scenario: Archived change in an older layout
- GIVEN an archived change whose proposal's Impact is free text and whose design has decisions without a Status line
- WHEN `wm check` runs
- THEN it reports no problem in that change

### Requirement: Items say how they are done
Every task item of an active change SHALL have a `- **Build:**` line, a `- **Criteria:**` line and a `- **Verify:**` line. The Build line SHALL be `planner` or `delegate`. `wm check` SHALL report an item without one of them, naming the line it lacks.

#### Scenario: Item without verification
- GIVEN an active change whose item 1.2 has a Build line and a Criteria line, and no Verify line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Verify:**`

#### Scenario: Item without a Build line
- GIVEN an active change whose item 1.2 has a Criteria line and a Verify line, and no Build line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Build:**` and the values `planner` and `delegate`

### Requirement: Decisions weigh options
Every decision in an active change's design SHALL name at least two options as nested bullets under its `- **Options:**` line, one option per bullet. `wm check` SHALL report a decision with fewer than two bullets, and an Options line with text of its own, asking for one option per bullet.

#### Scenario: One option
- GIVEN an active change whose design has a decision whose `- **Options:**` line has one bullet under it, `cut after sorting`
- WHEN `wm check` runs
- THEN it reports an error on that decision that asks for at least two options

#### Scenario: Options as a list
- GIVEN an active change whose design has a decision whose `- **Options:**` line is followed by two bullets
- WHEN `wm check` runs
- THEN it reports no problem with that decision's options

#### Scenario: Options on one line
- GIVEN an active change whose design has a decision with the line `- **Options:** cut before or after sorting` and no bullets under it
- WHEN `wm check` runs
- THEN it reports an error on that line that asks for one option per bullet

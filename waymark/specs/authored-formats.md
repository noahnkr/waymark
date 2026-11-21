# Authored formats

## Purpose

The layouts of what humans and the planner write in the record: the proposal's facts, Impact and Outcome, the charter's glossary, goals, constraints and rule headings, a task item's criteria, verification and build line, a delta's sections, a design's decisions and open questions, a milestone's file, and the examples the templates carry. What `wm` writes is in the `records` spec, and an exploration's status in the `explorations` spec.

## Requirements

### Requirement: Proposal facts as a list
A proposal's facts SHALL be bullet lines between its title and its first section: `- **Owner:** <name>` and `- **Review:** <level>`, and optionally `- **Milestone:** <name>`, `- **After:** <change>` and `- **Path:** short`. `wm new change` SHALL write them so. A fact written without the bullet SHALL NOT be read as a fact.

#### Scenario: New change
- GIVEN a project with git user Ada and `default_review` `self`
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- **Owner:** Ada`, `- **Path:** short` and `- **Review:** self` under its title

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

### Requirement: Record format 1
This version of `wm` SHALL write and read only record format 1, and no command SHALL migrate a record. A record in any other format, older or newer, SHALL be refused by `wm update`, by `wm init` in a clone and by every command that writes the record, and reported by `wm check` and `wm doctor`, each with one reason: it names the record's format, says this `wm` reads only format 1, and says to install the `wm` version that wrote it. A refusal SHALL change nothing.

#### Scenario: New record
- GIVEN a git repository with no record
- WHEN `wm init` runs
- THEN `waymark/config.toml` holds `record_format = 1`

#### Scenario: Record from wm 0.2.0
- GIVEN a record at format 3, pinned to the running `wm`
- WHEN `wm update` runs
- THEN it is refused with a reason that names format 3, says this `wm` reads only format 1 and says to install the `wm` version that wrote it, and no file changes

#### Scenario: Reported by the checks
- GIVEN a record at format 2, pinned to the running `wm`
- WHEN `wm check` runs
- THEN it reports the record's format with the same reason, and no message names `wm update`

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
`wm archive` SHALL take `--built` and `--differs` instead of `--outcome`, each one or more times, and SHALL write them under the archived proposal's `## Outcome` as a `- **Built:**` and a `- **Differs:**` line. A value given once SHALL be written on its label's line, as `- **Built:** <text>`. Several values SHALL be written as nested bullets under the label, one per value, in the order given. `--differs` MAY be left out, and SHALL then be written as `none`. `wm pr` SHALL show both, with their nested bullets.

#### Scenario: Archived with an outcome
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has the lines `- **Built:** The result limit.` and `- **Differs:** Fifty, not twenty.`

#### Scenario: Nothing differs
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit."`
- THEN the archived proposal's Outcome has the line `- **Differs:** none`

#### Scenario: Outcome as a list
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --built "A flag to change it." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has `- **Built:**`, then `  - The result limit.` and `  - A flag to change it.`, then `- **Differs:** Fifty, not twenty.`

### Requirement: Numbered goals, constraints and rules
The charter's Goals, Constraints and Rules SHALL be numbered lists, `1. <text>`, numbered from 1 without gaps; Rules MAY be empty. `wm check` SHALL report a line in another form, a heading under Rules included, or a number out of order, with the form expected.

#### Scenario: Bulleted goal
- GIVEN a charter whose Goals hold the line `- Answers in one step.`
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form `1. <text>`

#### Scenario: Step heading under Rules
- GIVEN a charter whose Rules hold the heading `### Apply` and the line `1. Run the full checks.`
- WHEN `wm check` runs
- THEN it reports an error on the heading that shows the form `1. <text>`

#### Scenario: No rules
- GIVEN a charter whose Rules section holds only a comment
- WHEN `wm check` runs
- THEN it reports nothing about the Rules

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

### Requirement: Template examples
Each template `wm` writes for a proposal, delta, design, task list, charter or exploration SHALL carry, in a comment, a good and a bad example of its content. The comments SHALL be left out of what `wm` checks and fingerprints.

#### Scenario: New proposal
- WHEN the planner runs `wm new change add-limit`
- THEN the proposal holds a comment with a good and a bad example, and `wm check` reports no problem in the comment

### Requirement: New work only
`wm check` SHALL hold active changes, the charter and explorations to the layouts of the requirements "Structured impact", "Numbered goals and constraints", "Settled decisions", "Items say how they are done", "Item lines in order" and "Decisions weigh options". An archived change SHALL be read as it was written, and SHALL NOT be reported for them.

#### Scenario: Archived change in an older layout
- GIVEN an archived change whose proposal's Impact is free text and whose design has decisions without a Status line
- WHEN `wm check` runs
- THEN it reports no problem in that change

### Requirement: Items say how they are done
Every task item of an active change SHALL have a `- **Build:**` line, a `- **Criteria:**` line and a `- **Verify:**` line. The Build line SHALL be `planner`, `implementer` or `human`. `wm check` SHALL report an item without one of them, naming the line it lacks.

#### Scenario: Item without verification
- GIVEN an active change whose item 1.2 has a Build line and a Criteria line, and no Verify line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Verify:**`

#### Scenario: Item without a Build line
- GIVEN an active change whose item 1.2 has a Criteria line and a Verify line, and no Build line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- **Build:**` and the values `planner`, `implementer` and `human`

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

### Requirement: Spec background
A spec MAY have a `## Background` section, after its Purpose and before its Requirements, holding the facts about its area that aren't requirements. A delta MAY have a `## Background` section; archiving or syncing the change SHALL set the spec's Background to the delta's, whole, adding the section when the spec has none. `wm check` SHALL report as an error an empty Background section in a spec or a delta.

#### Scenario: Background set by a delta
- GIVEN a spec `lead-nurture` with no Background, and a change whose delta for it has a Background holding "Leads come from A Place for Mom."
- WHEN the change is archived
- THEN the spec has a `## Background` section after its Purpose holding "Leads come from A Place for Mom.", and its requirements are unchanged

#### Scenario: Background replaced
- GIVEN a spec whose Background holds "Leads come from A Place for Mom.", and a change whose delta's Background holds "Leads come from A Place for Mom and Caring.com."
- WHEN the change is archived
- THEN the spec's Background holds only "Leads come from A Place for Mom and Caring.com."

#### Scenario: Empty background
- GIVEN an active change whose delta has a `## Background` heading with nothing under it
- WHEN `wm check` runs
- THEN it reports an error on that heading that says the Background is empty

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
- GIVEN an active change whose item 1.2 has its `- **Criteria:**` and `- **Verify:**` lines, then `- **Build:** implementer`
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names the order Build, Repo, Criteria, Verify

#### Scenario: Lines in order
- GIVEN an active change whose item 1.2 has `- **Build:** planner`, `- **Criteria:**` with two bullets, and `- **Verify:**`, in that order
- WHEN `wm check` runs
- THEN it reports no problem on item 1.2

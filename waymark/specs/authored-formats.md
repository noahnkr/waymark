# Authored formats

## Purpose

The layouts of what humans and the planner write in the record: the proposal's facts, Impact and Outcome, the charter's glossary, goals, constraints and rule headings, a task item's criteria, verification and build line, a delta's sections, a design's decisions and open questions, a milestone's file, an exploration's status, and the examples the templates carry. What `wm` writes is in the `records` spec.

## Requirements

### Requirement: Proposal facts as a list
A proposal's facts SHALL be bullet lines between its title and its first section: `- Owner: <name>`, and optionally `- Review: <level>` and `- Path: short`. `wm new change` SHALL write them so. A fact written without the bullet SHALL NOT be read as a fact.

#### Scenario: New change
- GIVEN a project with git user Ada
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- Owner: Ada` and `- Path: short` under its title

#### Scenario: Fact without a bullet
- GIVEN an active change whose proposal has the line `Owner: Ada` without a bullet, and no `- Owner:` line
- WHEN `wm check` runs
- THEN it reports that the proposal has no owner, and no message names `wm update`

### Requirement: Glossary as a list
The charter's glossary SHALL be a list of `- **<term>**: <meaning>` lines. `wm check` SHALL report a glossary line in another form as an error that shows the form. Step headings under Rules SHALL be read in any case, the template SHALL write them capitalized, such as `### Apply`, and a step with no rules MAY leave its heading out.

#### Scenario: Old glossary line
- GIVEN a charter whose glossary has the line `Record: everything in waymark/`
- WHEN `wm check` runs
- THEN it reports an error that shows the form `- **<term>**: <meaning>`

### Requirement: Criteria and verification as nested lists
A task item's `- Criteria:` and `- Verify:` lines MAY each be followed by a nested list, one criterion or one verification step per bullet, indented under it. The item's criteria SHALL be the `Criteria:` line's own text and every bullet under it, in order, and its verification SHALL be the `Verify:` line's own text and every bullet under it, in order. Both SHALL be part of the definition the human accepts.

#### Scenario: Nested criteria
- GIVEN an item with `- Criteria:` and, under it, the bullets `fifty at most` and `sorted by score`
- WHEN the planner runs `wm context <change> <item> --for implement`
- THEN the item's criteria in the pack list both bullets

#### Scenario: Nested verification
- GIVEN an item with `- Verify:` and, under it, the bullets `a test for the limit` and `wm check here`
- WHEN the planner runs `wm context <change> <item> --for implement`
- THEN the item's verification in the pack lists both bullets

### Requirement: Delta sections
A delta's sections SHALL be `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements`. Under RENAMED, each rename SHALL be a `- From: <old name>` line followed by a `- To: <new name>` line. Archiving or syncing the change SHALL rename the requirement in the spec and keep its statement and scenarios. A rename whose old name the spec doesn't have, or whose new name it already has, SHALL be a conflict. `wm check` SHALL report a section heading that matches one of these in another case, showing the heading it expects.

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

### Requirement: Exploration status
An exploration SHALL say where it stands in a `- Status:` line under its title: `open`, `parked`, or `led-to` followed by a link to the change or milestone it led to. The `- Status:` line alone SHALL say whether it is parked. A parked exploration SHALL say why in its Conclusion. `wm check` SHALL report a missing status as `missing-status`, an unknown status, a parked exploration with an empty Conclusion, and a `led-to` link that doesn't resolve.

#### Scenario: Parked exploration
- GIVEN an exploration with `- Status: parked` and the Conclusion "Waits for a second user."
- WHEN the planner runs `wm context --for explore`
- THEN the exploration is listed as parked

#### Scenario: Parked without a reason
- GIVEN an exploration with `- Status: parked` and an empty Conclusion
- WHEN `wm check` runs
- THEN it reports an error that asks for the reason in the Conclusion

#### Scenario: Missing status
- GIVEN an exploration with no `- Status:` line
- WHEN `wm check` runs
- THEN it reports `missing-status`, and the message asks for a `- Status:` line without naming `wm update`

#### Scenario: Parked in the Conclusion only
- GIVEN an exploration with `- Status: open` and the Conclusion "Parked: waits for a second user."
- WHEN the planner runs `wm context --for explore`
- THEN the exploration is listed as open

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
A proposal's `## Impact` section SHALL hold a `- Specs:` line, a `- User-visible:` line and a `- Code:` line, each followed by text or by nested bullets. `Specs:` SHALL name each spec the change has a delta for, in backticks, or say `none`. `wm check` SHALL report a missing line, a spec named under `Specs:` that has no delta in the change, and a delta whose spec isn't named.

#### Scenario: Impact matches the deltas
- GIVEN an active change with a delta for `search` and the line `- Specs: `search` (modified)`
- WHEN `wm check` runs
- THEN it reports no problem in the Impact

#### Scenario: Delta not named in the impact
- GIVEN an active change with deltas for `search` and `ranking` and the line `- Specs: `search` (modified)`
- WHEN `wm check` runs
- THEN it reports an error on the proposal that names `ranking`

### Requirement: Structured outcome
`wm archive` SHALL take `--built` and `--differs` instead of `--outcome`, and SHALL write them as `- Built: <text>` and `- Differs: <text>` lines under the archived proposal's `## Outcome`. `--differs` MAY be left out, and SHALL then be written as `none`. `wm pr` SHALL show both lines.

#### Scenario: Archived with an outcome
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit." --differs "Fifty, not twenty."`
- THEN the archived proposal's Outcome has the lines `- Built: The result limit.` and `- Differs: Fifty, not twenty.`

#### Scenario: Nothing differs
- GIVEN an applied change
- WHEN the planner runs `wm archive <change> --built "The result limit."`
- THEN the archived proposal's Outcome has the line `- Differs: none`

### Requirement: Numbered goals and constraints
The charter's Goals and Constraints SHALL be numbered lists, `1. <text>`, numbered from 1 without gaps. `wm check` SHALL report a line in another form, or a number out of order, with the form expected.

#### Scenario: Bulleted goal
- GIVEN a charter whose Goals hold the line `- Answers in one step.`
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form `1. <text>`

### Requirement: Settled decisions
Each `### Decision:` in a design SHALL have a `- Status:` line, `proposed` or `decided`, and a `- Decided by:` line, `human` or `planner`. A design SHALL have an `## Open questions` section, holding a list of questions or the word `None.`. `wm check` SHALL report a missing or unknown value. `wm accept` SHALL refuse a change while a decision is `proposed` or an open question is listed, naming each one.

#### Scenario: Proposed decision
- GIVEN a change whose design has a decision with `- Status: proposed`
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
`wm check` SHALL hold active changes, the charter and explorations to the layouts of the requirements "Structured impact", "Numbered goals and constraints" and "Settled decisions". An archived change SHALL be read as it was written, and SHALL NOT be reported for them.

#### Scenario: Archived change in an older layout
- GIVEN an archived change whose proposal's Impact is free text and whose design has decisions without `- Status:`
- WHEN `wm check` runs
- THEN it reports no problem in that change

### Requirement: Milestone as one file
A milestone SHALL be a folder holding one file, `milestone.md`: a title, then the sections `## Goal`, `## Done when`, `## Non-goals` and `## Roadmap`, in that order. `wm new milestone` SHALL write it so. The list lines under `## Roadmap`, and only those, SHALL be the milestone's roadmap entries. `wm check` SHALL report any other file in an active milestone's folder as an error that names `milestone.md`.

#### Scenario: New milestone
- WHEN the planner runs `wm new milestone faster-search`
- THEN the folder `milestones/faster-search` holds only `milestone.md`, with the four sections in order

#### Scenario: Other file in a milestone
- GIVEN an active milestone folder holding `milestone.md` and `notes.md`
- WHEN `wm check` runs
- THEN it reports an error on `notes.md` that names `milestone.md`

#### Scenario: Roadmap ticked at archive
- GIVEN a milestone whose `## Roadmap` links to the change `add-limit`, and whose `## Done when` holds a bullet
- WHEN `add-limit` is archived
- THEN the roadmap line links to the archived change and `wm status` counts it as archived, and the `## Done when` bullet is unchanged and isn't counted as a roadmap entry

### Requirement: Items say how they are done
Every task item of an active change SHALL have a `- Criteria:` line and a `- Verify:` line. `wm check` SHALL report an item without one of them, naming the line it lacks.

#### Scenario: Item without verification
- GIVEN an active change whose item 1.2 has a `- Criteria:` line and no `- Verify:` line
- WHEN `wm check` runs
- THEN it reports an error on item 1.2 that names `- Verify:`

### Requirement: Decisions weigh options
Every decision in an active change's design SHALL name at least two options under `- Options:`: two or more nested bullets, or one line naming them joined by "or" or ";". `wm check` SHALL report a decision with fewer than two.

#### Scenario: One option
- GIVEN an active change whose design has a decision with the line `- Options: cut after sorting`
- WHEN `wm check` runs
- THEN it reports an error on that decision that asks for at least two options

#### Scenario: Options as a list
- GIVEN an active change whose design has a decision whose `- Options:` line is followed by two bullets
- WHEN `wm check` runs
- THEN it reports no problem with that decision's options

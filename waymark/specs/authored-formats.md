# Authored formats

## Purpose

The layouts of what humans and the planner write in the record: the proposal's facts, the charter's glossary and rule headings, a task item's criteria and build line, a delta's sections, and an exploration's status. What `wm` writes is in the `records` spec.

## Requirements

### Requirement: Proposal facts as a list
A proposal's facts SHALL be bullet lines between its title and its first section: `- Owner: <name>`, and optionally `- Review: <level>` and `- Path: short`. `wm new change` SHALL write them so. `wm check` SHALL report a fact written without the bullet as an old layout, naming `wm update`.

#### Scenario: New change
- GIVEN a project with git user Ada
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the lines `- Owner: Ada` and `- Path: short` under its title

#### Scenario: Old fact line
- GIVEN an active change whose proposal has the line `Owner: Ada` without a bullet
- WHEN `wm check` runs
- THEN it reports an error on that line that names `wm update`

### Requirement: Glossary as a list
The charter's glossary SHALL be a list of `- **<term>**: <meaning>` lines. `wm check` SHALL report a glossary line in another form as an error that shows the form. Step headings under Rules SHALL be read in any case, the template SHALL write them capitalized, such as `### Apply`, and a step with no rules MAY leave its heading out.

#### Scenario: Old glossary line
- GIVEN a charter whose glossary has the line `Record: everything in waymark/`
- WHEN `wm check` runs
- THEN it reports an error that shows the form `- **<term>**: <meaning>`

### Requirement: Criteria as a nested list
A task item's `- Criteria:` line MAY be followed by a nested list, one criterion per bullet, indented under it. The item's criteria SHALL be the line's own text and every bullet under it, in order, and they SHALL be part of the definition the human accepts.

#### Scenario: Nested criteria
- GIVEN an item with `- Criteria:` and, under it, the bullets `fifty at most` and `sorted by score`
- WHEN the planner runs `wm context <change> <item> --for implement`
- THEN the item's criteria in the pack list both bullets

### Requirement: Delta sections
A delta's sections SHALL be `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements` and `## RENAMED Requirements`. Under RENAMED, each rename SHALL be a `- From: <old name>` line followed by a `- To: <new name>` line. Archiving or syncing the change SHALL rename the requirement in the spec and keep its statement and scenarios. A rename whose old name the spec doesn't have, or whose new name it already has, SHALL be a conflict. `wm check` SHALL report a section with an old heading as an old layout, naming `wm update`.

#### Scenario: Requirement renamed
- GIVEN a spec with the requirement "Result cap"
- WHEN a change whose delta renames "Result cap" to "Result limit" is archived
- THEN the spec has the requirement "Result limit" with the same statement and scenarios, and no "Result cap"

#### Scenario: Rename of a missing requirement
- GIVEN a spec without the requirement "Result cap"
- WHEN a change's delta renames "Result cap" to "Result limit"
- THEN `wm check` reports a conflict on that delta

### Requirement: Exploration status
An exploration SHALL say where it stands in a `- Status:` line under its title: `open`, `parked`, or `led-to` followed by a link to the change or milestone it led to. A parked exploration SHALL say why in its Conclusion. `wm check` SHALL report a missing or unknown status, a parked exploration with an empty Conclusion, and a `led-to` link that doesn't resolve.

#### Scenario: Parked exploration
- GIVEN an exploration with `- Status: parked` and the Conclusion "Waits for a second user."
- WHEN the planner runs `wm context --for explore`
- THEN the exploration is listed as parked

#### Scenario: Parked without a reason
- GIVEN an exploration with `- Status: parked` and an empty Conclusion
- WHEN `wm check` runs
- THEN it reports an error that asks for the reason in the Conclusion

### Requirement: Record format 3
This version of `wm` SHALL write and read only record format 3, and SHALL NOT migrate a record in an older format. `wm update` SHALL refuse such a record with a reason that names its format and says this `wm` doesn't migrate it, and SHALL change nothing.

#### Scenario: Older record
- GIVEN a record in format 2
- WHEN `wm update` runs
- THEN it is refused with a reason that names format 2, and no file changes

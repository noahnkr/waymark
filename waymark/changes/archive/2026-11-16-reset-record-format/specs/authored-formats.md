# Authored formats

## MODIFIED Requirements

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

## RENAMED Requirements

- **From:** Record format 3
- **To:** Record format 1

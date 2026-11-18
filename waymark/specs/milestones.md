# Milestones

## Purpose

A milestone: a goal several changes work toward, the roadmap that lists them, and how a change belongs to one. What a milestone holds, how a change names its milestone and is checked against the roadmap, and what the agents of a member change see of it.

## Requirements

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

### Requirement: Change names its milestone
A change SHALL belong to a milestone when its proposal has a `- Milestone: <name>` line naming an active milestone's folder, and that milestone's roadmap links the change's proposal. A change without the line SHALL belong to no milestone. For an active change, `wm check` SHALL report an error when its proposal names a milestone that doesn't exist, when the named milestone's roadmap doesn't link the change, when a roadmap links the change and its proposal names no milestone or another one, or when more than one roadmap links the change. Archived changes SHALL NOT be checked against roadmaps.

#### Scenario: Proposal and roadmap agree
- GIVEN an active change `add-limit` whose proposal has `- Milestone: faster-search`, and the milestone `faster-search` whose roadmap links to `add-limit`'s proposal
- WHEN `wm check` runs
- THEN it reports no problem about the change's milestone

#### Scenario: Roadmap doesn't link the change
- GIVEN an active change `add-limit` whose proposal has `- Milestone: faster-search`, and a roadmap in `faster-search` with no link to `add-limit`
- WHEN `wm check` runs
- THEN it reports an error on the proposal that names `faster-search` and says its roadmap doesn't link `add-limit`

#### Scenario: Linked change names no milestone
- GIVEN the milestone `faster-search` whose roadmap links to the active change `add-limit`, whose proposal has no `- Milestone:` line
- WHEN `wm check` runs
- THEN it reports an error on the proposal that says to add `- Milestone: faster-search`

#### Scenario: Unknown milestone
- GIVEN an active change whose proposal has `- Milestone: no-such-milestone`
- WHEN `wm check` runs
- THEN it reports an error that names `no-such-milestone` as a milestone that doesn't exist

### Requirement: New change in a milestone
`wm new change <name> --milestone <milestone>` SHALL write the `- Milestone: <milestone>` line in the new proposal, under the `- Owner:` line, and SHALL link the change from the milestone's roadmap: a roadmap line that doesn't link anywhere and starts with the change's name SHALL become a link to the new proposal and keep the text after the name; otherwise a line linking the proposal SHALL be added at the end of the roadmap. It SHALL refuse a milestone that isn't an active milestone, and write nothing.

#### Scenario: Planned roadmap line
- GIVEN the milestone `faster-search` whose roadmap has the line `- add-limit: cap the results`
- WHEN the planner runs `wm new change add-limit --milestone faster-search`
- THEN the proposal has the line `- Milestone: faster-search`, the roadmap line reads `- [add-limit](../../changes/add-limit/proposal.md): cap the results`, and `wm check` reports no problem about the change's milestone

#### Scenario: Change not on the roadmap
- GIVEN the milestone `faster-search` whose roadmap has no line for `add-limit`
- WHEN the planner runs `wm new change add-limit --milestone faster-search`
- THEN the roadmap ends with the line `- [add-limit](../../changes/add-limit/proposal.md)`

#### Scenario: Unknown milestone refused
- GIVEN no milestone named `no-such-milestone`
- WHEN the planner runs `wm new change add-limit --milestone no-such-milestone`
- THEN it is refused with a message that names `no-such-milestone`, and no change folder is created

### Requirement: Milestone in the context packs
The implement and review context packs of a change that belongs to a milestone SHALL carry the milestone's name, its `## Goal` and its `## Non-goals`, in the text and in the JSON. The packs of a change that belongs to no milestone SHALL carry no milestone.

#### Scenario: Member change's packs
- GIVEN an accepted change `add-limit` that belongs to the milestone `faster-search`
- WHEN the planner runs `wm context add-limit 1.1 --for implement`, and later `wm context add-limit --for review`
- THEN each pack holds the name `faster-search`, the text of its Goal and the text of its Non-goals, and neither holds its Done when or its roadmap

#### Scenario: Change without a milestone
- GIVEN an accepted change whose proposal has no `- Milestone:` line
- WHEN `wm context <change> 1.1 --for implement --json` runs
- THEN the pack's `milestone` is null

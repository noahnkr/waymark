# Milestones

## MODIFIED Requirements

### Requirement: Change names its milestone
A change SHALL belong to a milestone when its proposal has a `- **Milestone:** <name>` line naming an active milestone's folder, and that milestone's roadmap links the change's proposal. A change without the line SHALL belong to no milestone. For an active change, `wm check` SHALL report an error when its proposal names a milestone that doesn't exist, when the named milestone's roadmap doesn't link the change, when a roadmap links the change and its proposal names no milestone or another one, or when more than one roadmap links the change. Archived changes SHALL NOT be checked against roadmaps.

#### Scenario: Proposal and roadmap agree
- GIVEN an active change `add-limit` whose proposal has `- **Milestone:** faster-search`, and the milestone `faster-search` whose roadmap links to `add-limit`'s proposal
- WHEN `wm check` runs
- THEN it reports no problem about the change's milestone

#### Scenario: Roadmap doesn't link the change
- GIVEN an active change `add-limit` whose proposal has `- **Milestone:** faster-search`, and a roadmap in `faster-search` with no link to `add-limit`
- WHEN `wm check` runs
- THEN it reports an error on the proposal that names `faster-search` and says its roadmap doesn't link `add-limit`

#### Scenario: Linked change names no milestone
- GIVEN the milestone `faster-search` whose roadmap links to the active change `add-limit`, whose proposal has no `- **Milestone:**` line
- WHEN `wm check` runs
- THEN it reports an error on the proposal that says to add `- **Milestone:** faster-search`

#### Scenario: Unknown milestone
- GIVEN an active change whose proposal has `- **Milestone:** no-such-milestone`
- WHEN `wm check` runs
- THEN it reports an error that names `no-such-milestone` as a milestone that doesn't exist

### Requirement: New change in a milestone
`wm new change <name> --milestone <milestone>` SHALL write the `- **Milestone:** <milestone>` line in the new proposal, under the `- **Owner:**` line, and SHALL link the change from the milestone's roadmap: a roadmap line that doesn't link anywhere and starts with the change's name SHALL become a link to the new proposal and keep the text after the name; otherwise a line linking the proposal SHALL be added at the end of the roadmap. It SHALL write a `(proposed)` record naming the change in the milestone's Log. It SHALL refuse a milestone that isn't an active milestone, and write nothing.

#### Scenario: Planned roadmap line
- GIVEN the milestone `faster-search` whose roadmap has the line `- add-limit: cap the results`
- WHEN the planner, Ada, runs `wm new change add-limit --milestone faster-search` on 2026-11-20
- THEN the proposal has the line `- **Milestone:** faster-search`, the roadmap line reads `- [add-limit](../../changes/add-limit/proposal.md): cap the results`, the milestone's Log holds `(proposed) 2026-11-20 add-limit by Ada`, and `wm check` reports no problem about the change's milestone

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
- GIVEN an accepted change whose proposal has no `- **Milestone:**` line
- WHEN `wm context <change> 1.1 --for implement --json` runs
- THEN the pack's `milestone` is null

### Requirement: Roadmap changed through wm
`wm roadmap add <milestone> <change> "<description>"` SHALL add the planned line `- <change>: <description>` at the end of an active milestone's roadmap, and SHALL refuse a name that isn't a valid change name or is already on the roadmap. `wm roadmap drop <milestone> <change> --reason "<why>"` SHALL remove the change's line, and SHALL refuse a line whose change is active and names the milestone, saying to take the `- **Milestone:**` line off its proposal, or to archive or delete the change, first. `wm roadmap move <milestone> <change> --after <other>` SHALL put the change's line right after the other's, and `--first` at the top of the roadmap. Each command SHALL refuse a milestone that isn't active, or a change that isn't on the roadmap where it needs one, and write nothing when it refuses.

#### Scenario: Line added
- GIVEN the active milestone `faster-search` whose roadmap has one line, for `add-limit`
- WHEN the planner runs `wm roadmap add faster-search add-cache "cache hot queries"`
- THEN the roadmap's lines are the one for `add-limit`, then `- add-cache: cache hot queries`

#### Scenario: Line moved
- GIVEN a roadmap with lines for `add-limit`, `add-cache` and `add-index`, in that order
- WHEN the planner runs `wm roadmap move faster-search add-index --after add-limit`, then `wm roadmap move faster-search add-cache --first`
- THEN the lines are in the order `add-cache`, `add-limit`, `add-index`

#### Scenario: Planned line dropped
- GIVEN a roadmap with the planned line `- add-cache: cache hot queries`
- WHEN the planner runs `wm roadmap drop faster-search add-cache --reason "the index is fast enough"`
- THEN the roadmap has no line for `add-cache`

#### Scenario: Active member not dropped
- GIVEN the active change `add-limit`, whose proposal has `- **Milestone:** faster-search` and whose line the roadmap links
- WHEN the planner runs `wm roadmap drop faster-search add-limit --reason "later"`
- THEN it is refused with a message that names the `- **Milestone:**` line, and the roadmap is unchanged

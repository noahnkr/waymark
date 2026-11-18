# Milestones

## MODIFIED Requirements

### Requirement: Milestone as one file
A milestone SHALL be a folder holding one file, `milestone.md`: a title, then the sections `## Goal`, `## Done when`, `## Non-goals` and `## Roadmap`, in that order, and optionally a `## Log` section after them, last. `wm new milestone` SHALL write it so, without a Log. The list lines under `## Roadmap`, and only those, SHALL be the milestone's roadmap entries. `wm check` SHALL report any other file in an active milestone's folder as an error that names `milestone.md`, and a `## Log` section that isn't the last as an error.

#### Scenario: New milestone
- WHEN the planner runs `wm new milestone faster-search`
- THEN the folder `milestones/faster-search` holds only `milestone.md`, with the four sections in order and no `## Log`

#### Scenario: Other file in a milestone
- GIVEN an active milestone folder holding `milestone.md` and `notes.md`
- WHEN `wm check` runs
- THEN it reports an error on `notes.md` that names `milestone.md`

#### Scenario: Roadmap ticked at archive
- GIVEN a milestone whose `## Roadmap` links to the change `add-limit`, and whose `## Done when` holds a bullet
- WHEN `add-limit` is archived
- THEN the roadmap line links to the archived change and `wm status` counts it as archived, and the `## Done when` bullet is unchanged and isn't counted as a roadmap entry

#### Scenario: Log not last
- GIVEN an active milestone whose `## Log` section comes before its `## Roadmap`
- WHEN `wm check` runs
- THEN it reports an error that the `## Log` section is the last section of `milestone.md`

### Requirement: New change in a milestone
`wm new change <name> --milestone <milestone>` SHALL write the `- Milestone: <milestone>` line in the new proposal, under the `- Owner:` line, and SHALL link the change from the milestone's roadmap: a roadmap line that doesn't link anywhere and starts with the change's name SHALL become a link to the new proposal and keep the text after the name; otherwise a line linking the proposal SHALL be added at the end of the roadmap. It SHALL write a `(proposed)` record naming the change in the milestone's Log. It SHALL refuse a milestone that isn't an active milestone, and write nothing.

#### Scenario: Planned roadmap line
- GIVEN the milestone `faster-search` whose roadmap has the line `- add-limit: cap the results`
- WHEN the planner, Ada, runs `wm new change add-limit --milestone faster-search` on 2026-11-20
- THEN the proposal has the line `- Milestone: faster-search`, the roadmap line reads `- [add-limit](../../changes/add-limit/proposal.md): cap the results`, the milestone's Log holds `(proposed) 2026-11-20 add-limit by Ada`, and `wm check` reports no problem about the change's milestone

#### Scenario: Change not on the roadmap
- GIVEN the milestone `faster-search` whose roadmap has no line for `add-limit`
- WHEN the planner runs `wm new change add-limit --milestone faster-search`
- THEN the roadmap ends with the line `- [add-limit](../../changes/add-limit/proposal.md)`

#### Scenario: Unknown milestone refused
- GIVEN no milestone named `no-such-milestone`
- WHEN the planner runs `wm new change add-limit --milestone no-such-milestone`
- THEN it is refused with a message that names `no-such-milestone`, and no change folder is created

## ADDED Requirements

### Requirement: Roadmap changed through wm
`wm roadmap add <milestone> <change> "<description>"` SHALL add the planned line `- <change>: <description>` at the end of an active milestone's roadmap, and SHALL refuse a name that isn't a valid change name or is already on the roadmap. `wm roadmap drop <milestone> <change> --reason "<why>"` SHALL remove the change's line, and SHALL refuse a line whose change is active and names the milestone, saying to take the `- Milestone:` line off its proposal, or to archive or delete the change, first. `wm roadmap move <milestone> <change> --after <other>` SHALL put the change's line right after the other's, and `--first` at the top of the roadmap. Each command SHALL refuse a milestone that isn't active, or a change that isn't on the roadmap where it needs one, and write nothing when it refuses.

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
- GIVEN the active change `add-limit`, whose proposal has `- Milestone: faster-search` and whose line the roadmap links
- WHEN the planner runs `wm roadmap drop faster-search add-limit --reason "later"`
- THEN it is refused with a message that names the `- Milestone:` line, and the roadmap is unchanged

### Requirement: Milestone log
`wm` SHALL write a record into an active milestone's `## Log` section, creating the section at the end of `milestone.md` when needed, each time it changes the milestone's plan: `(added) <date> <change> [by <who>]: <description>` from `wm roadmap add`, `(dropped) <date> <change> [by <who>]: <reason>` from `wm roadmap drop`, `(moved) <date> <change> after <other>|first [by <who>]` from `wm roadmap move`, `(proposed) <date> <change> [by <who>]` from `wm new change --milestone`, and `(archived) <date> <change> [by <who>]` when a member change is archived. Records SHALL NOT be written for lines that were on the roadmap before the Log began.

#### Scenario: Log of a plan's changes
- GIVEN the active milestone `faster-search` with no `## Log` section
- WHEN Ada, on 2026-11-20, runs `wm roadmap add faster-search add-cache "cache hot queries"`, then `wm roadmap move faster-search add-cache --first`, then `wm roadmap drop faster-search add-cache --reason "the index is fast enough"`
- THEN `milestone.md` ends with a `## Log` section holding, in order, `(added) 2026-11-20 add-cache by Ada: cache hot queries`, `(moved) 2026-11-20 add-cache first by Ada` and `(dropped) 2026-11-20 add-cache by Ada: the index is fast enough`

#### Scenario: Member change archived
- GIVEN the active change `add-limit` that belongs to `faster-search`
- WHEN Ada archives it on 2026-11-21
- THEN the milestone's Log ends with `(archived) 2026-11-21 add-limit by Ada`

### Requirement: Roadmap lines written only by wm
An agent's edit to an active milestone's `milestone.md` that adds, changes or removes a roadmap line, or a record in its `## Log`, SHALL be refused with a reason that names `wm roadmap`. Edits to the milestone's other sections SHALL be allowed.

#### Scenario: Agent adds a roadmap line by hand
- GIVEN the active milestone `faster-search`
- WHEN the planner edits its `milestone.md` to add the line `- add-cache: cache hot queries` under `## Roadmap`
- THEN the edit is refused with a reason that names `wm roadmap add`

#### Scenario: Agent edits the goal
- GIVEN the active milestone `faster-search`
- WHEN the planner edits the text under its `## Goal`
- THEN the edit is allowed

### Requirement: Closing a milestone
`wm close <milestone>` SHALL close a milestone only when every line on its roadmap links to an archived change. It SHALL refuse a milestone with a planned line, naming it and saying to propose it or drop it with `wm roadmap drop`, and a milestone with a line whose change is still active, naming that change.

#### Scenario: Planned line keeps a milestone open
- GIVEN a milestone whose roadmap links one archived change and has the planned line `- add-cache: cache hot queries`
- WHEN the planner runs `wm close faster-search`
- THEN it is refused with a message that names `add-cache` and `wm roadmap drop`, and the milestone stays open

#### Scenario: Every line archived
- GIVEN a milestone whose roadmap lines all link archived changes
- WHEN the planner runs `wm close faster-search`
- THEN the milestone moves to `milestones/archive/<date>-faster-search/`

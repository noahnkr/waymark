# Milestones

## MODIFIED Requirements

### Requirement: New change in a milestone
`wm new change <name> --milestone <milestone>` SHALL write the `- **Milestone:** <milestone>` line in the new proposal, under the `- **Owner:**` line, and SHALL link the change from the milestone's roadmap: a roadmap line that doesn't link anywhere and starts with the change's name SHALL become a link to the new proposal and keep the text after the name; otherwise a line linking the proposal SHALL be added at the end of the roadmap. It SHALL write a `(proposed)` record naming the change in the milestone's Log. It SHALL refuse a milestone that isn't an active milestone, and write nothing.

#### Scenario: Planned roadmap line
- GIVEN the milestone `faster-search` whose roadmap has the line `- add-limit: cap the results`
- WHEN the planner, Ada, runs `wm new change add-limit --milestone faster-search` on 2026-11-20
- THEN the proposal has the line `- **Milestone:** faster-search`, the roadmap line reads `- [add-limit](../../changes/add-limit/proposal.md): cap the results`, the milestone's Log holds `2026-11-20 (proposed) add-limit by planner for Ada`, and `wm check` reports no problem about the change's milestone

#### Scenario: Change not on the roadmap
- GIVEN the milestone `faster-search` whose roadmap has no line for `add-limit`
- WHEN the planner runs `wm new change add-limit --milestone faster-search`
- THEN the roadmap ends with the line `- [add-limit](../../changes/add-limit/proposal.md)`

#### Scenario: Unknown milestone refused
- GIVEN no milestone named `no-such-milestone`
- WHEN the planner runs `wm new change add-limit --milestone no-such-milestone`
- THEN it is refused with a message that names `no-such-milestone`, and no change folder is created

### Requirement: Milestone log
`wm` SHALL write a record into an active milestone's `## Log` section, creating the section at the end of `milestone.md` when needed, each time it changes the milestone's plan: `<date> (added) <change> [by <who>]: <description>` from `wm roadmap add`, `<date> (dropped) <change> [by <who>]: <reason>` from `wm roadmap drop`, `<date> (moved) <change> after <other>|first [by <who>]` from `wm roadmap move`, `<date> (proposed) <change> [by <who>]` from `wm new change --milestone`, and `<date> (archived) <change> [by <who>]` when a member change is archived. Records SHALL NOT be written for lines that were on the roadmap before the Log began.

#### Scenario: Log of a plan's changes
- GIVEN the active milestone `faster-search` with no `## Log` section
- WHEN Ada, on 2026-11-20, runs `wm roadmap add faster-search add-cache "cache hot queries"`, then `wm roadmap move faster-search add-cache --first`, then `wm roadmap drop faster-search add-cache --reason "the index is fast enough"`
- THEN `milestone.md` ends with a `## Log` section holding, in order, `2026-11-20 (added) add-cache by planner for Ada: cache hot queries`, `2026-11-20 (moved) add-cache first by planner for Ada` and `2026-11-20 (dropped) add-cache by planner for Ada: the index is fast enough`

#### Scenario: Member change archived
- GIVEN the active change `add-limit` that belongs to `faster-search`
- WHEN Ada archives it on 2026-11-21
- THEN the milestone's Log ends with `2026-11-21 (archived) add-limit by Ada`


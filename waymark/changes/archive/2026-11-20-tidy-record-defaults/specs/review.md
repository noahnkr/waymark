# Review

## MODIFIED Requirements

### Requirement: Review level per change
A change's review level SHALL be the value of the `- **Review:**` line in its proposal: `self`, `independent` or `none`. `wm new change` SHALL write the line under the Owner line, holding the project's `default_review`, or `self` on the short path when the default is `independent`. On the short path the level SHALL be `self` or `none`. `wm check` SHALL report as an error an active change whose proposal has no Review line, an unknown value, or `independent` on the short path. It SHALL warn when the change's deltas modify or remove a requirement and the level isn't `independent`.

#### Scenario: Level from the proposal
- GIVEN a project whose `default_review` is `self`
- WHEN a change's proposal has the line `- **Review:** independent`
- THEN `wm show <change>` gives the review level `independent`

#### Scenario: Default written at creation
- GIVEN a project whose `default_review` is `independent`
- WHEN the planner runs `wm new change add-limit`
- THEN the proposal has the line `- **Review:** independent` under its Owner line

#### Scenario: Default on the short path
- GIVEN a project whose `default_review` is `independent`
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the line `- **Review:** self`

#### Scenario: Review line missing
- GIVEN an active change whose proposal has no `- **Review:**` line
- WHEN `wm check` runs
- THEN it reports an error on the proposal that shows the line `- **Review:** <level>` to add

#### Scenario: Risky change at self
- GIVEN a change whose deltas modify a requirement and whose review level is `self`
- WHEN `wm check` runs
- THEN it warns that a change that modifies or removes a requirement should be reviewed independently

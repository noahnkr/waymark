# Review

## Purpose

How a change is checked before it is archived: one review of the whole change at the change's review level, how it is recorded with its findings, what a request for changes reopens, and what goes to the human.

## Added requirements

### Requirement: Review level per change
A change's review level SHALL be the value of the `Review:` line in its proposal (`self`, `independent` or `none`), or the project's `default_review` when the line is absent. On the short path it SHALL be `self` or `none`. `wm check` SHALL report an unknown value, or `independent` on the short path, as an error. It SHALL warn when the change's deltas modify or remove a requirement and the level isn't `independent`.

#### Scenario: Level from the proposal
- GIVEN a project whose `default_review` is `self`
- WHEN a change's proposal has the line `Review: independent`
- THEN `wm show <change>` gives the review level `independent`

#### Scenario: Risky change at self
- GIVEN a change whose deltas modify a requirement and whose review level is `self`
- WHEN `wm check` runs
- THEN it warns that a change that modifies or removes a requirement should be reviewed independently

### Requirement: One review per change
When every item of an accepted change is ticked and the change isn't reviewed, `wm instructions` SHALL make the next step a review of the whole change. At `self` the planner records it. At `independent` a reviewer agent is started with the change's name and nothing else. At `none` no review is needed.

#### Scenario: All items ticked
- GIVEN an accepted change at review level `self` with every item ticked and no review recorded
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is the review of the change, and the command is `wm review <change> --self "<summary>"`

#### Scenario: An item still to build
- GIVEN an accepted change with item 1.1 ticked and item 1.2 not ticked
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is to apply item 1.2, not a review

### Requirement: Review recorded in the task list
`wm` SHALL write the review of a change as a `(review)` or `(self-review)` line in a `## Review` section at the end of the change's task list, creating the section if needed. It SHALL write each finding under its record as a sub-line with a severity (`critical`, `warning` or `suggestion`), a place and a text. It SHALL refuse a `pass` verdict, or a self-review, that comes with a critical finding.

#### Scenario: Self-review with a finding
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --finding "warning: src/a.py:12: <text>"`
- THEN the task list ends with a `## Review` section holding a `(self-review)` line with the summary and, under it, the warning with its place and text

#### Scenario: Pass with a critical finding
- GIVEN a change waiting for an independent review
- WHEN a `pass` verdict comes with a `critical` finding
- THEN it is refused with the reason, and nothing is written

### Requirement: Changes reopen the named items
A `changes` verdict SHALL name the items to rebuild, and `wm` SHALL refuse one that names none, or names an item the change doesn't have. The named items SHALL be the next to apply, each reopened with `wm reopen`. Once they are ticked again, the change SHALL need an independent review, whatever its level.

#### Scenario: Two items named
- GIVEN a change at review level `self` with items 1.1, 1.2 and 2.1 ticked
- WHEN a verdict of `changes` naming items 1.2 and 2.1 is recorded
- THEN the next step is to reopen and apply item 1.2, then item 2.1, and once both are ticked again the next step is an independent review

### Requirement: Escalation to the human
A second `changes` verdict on a change, or a `spec-gap` verdict, SHALL send the change to the human: it appears in `wm inbox`, and no step is offered to the planner until the human's decision is recorded with `wm resolve <change> "<what was decided>"`.

#### Scenario: Second request for changes
- GIVEN a change with one `changes` verdict whose named items have been rebuilt
- WHEN a second `changes` verdict is recorded
- THEN `wm inbox` lists the change with the verdict's reasons, and `wm instructions` names no step for the planner

### Requirement: Archive needs the change's review
`wm archive` SHALL refuse a change that needs a review and has no passing one, unless the human overrides it with a reason, which is written into the outcome. A change at level `none` SHALL need no review.

#### Scenario: Not reviewed
- GIVEN a change at review level `self` with every item ticked and no review
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names the missing review

### Requirement: No review tag on items
In an active change, a `review:` tag on a task item SHALL be reported by `wm check` as an error that says the review level is now set in the proposal. Archived changes SHALL be shown as they were written, including their item reviews.

#### Scenario: Old tag
- GIVEN an active change with an item ending in `` `review: independent` ``
- WHEN `wm check` runs
- THEN it reports an error on that item that points to the proposal's `Review:` line

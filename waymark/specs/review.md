# Review

## Purpose

How a change is checked before it is archived: one review of the whole change at the change's review level, how it is recorded with its findings, what a request for changes reopens, and what goes to the human.

## Requirements

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
`wm` SHALL write the review of a change as a `(review)` or `(self-review)` record in the `## Log` section at the end of the change's task list, creating the section if needed. It SHALL write each finding under its record as a sub-line with a severity (`critical`, `warning` or `suggestion`), its place in backticks, and a text. It SHALL refuse a `pass` verdict, or a self-review, that comes with a critical finding.

#### Scenario: Self-review with a finding
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --finding "warning: src/a.py:12: <text>"`
- THEN the task list ends with a `## Log` section holding a `(self-review)` record with the summary and, under it, ``- warning `src/a.py:12`: <text>``

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
`wm archive` SHALL refuse a change that needs a review and has no passing one, unless the human overrides it with a reason. The override SHALL be written as an `(override)` record in the change's Log, and `wm pr` SHALL show it. A change at level `none` SHALL need no review.

#### Scenario: Not reviewed
- GIVEN a change at review level `self` with every item ticked and no review
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names the missing review

#### Scenario: Overridden
- GIVEN a change at review level `self` with every item ticked and no review
- WHEN the human runs `wm archive <change> --override "<reason>"`
- THEN the archived change's Log holds an `(override)` record with the reason, and `wm pr` shows it

### Requirement: Review of items added after a review
Every `(review)` and `(self-review)` record SHALL name the items it covers, as `covers <item> <item>...` before who wrote it; `wm` SHALL write every item of the change at the time, or the items that review was of. A record without `covers` SHALL cover every item. When every item is ticked and some item is covered by no passing review or self-review, `wm instructions` SHALL make the next step a review of those items only, at the change's level, and the record it writes SHALL cover just them. `wm archive` SHALL refuse such a change unless the human overrides it with a reason, as it refuses an unreviewed one.

#### Scenario: Item added after a pass
- GIVEN an accepted change at review level `independent` whose items 1.1 and 1.2 passed a review covering them
- WHEN item 1.3 is added, built and ticked
- THEN the next step is a review of item 1.3 only, the reviewer can be started with the change's name, and its passing verdict is written as `(review) <date> pass covers 1.3 by wm-reviewer: <reasons>`

#### Scenario: Archive before the added item is reviewed
- GIVEN the same change with item 1.3 ticked and no review covering it
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names item 1.3 as not reviewed

#### Scenario: Older review records
- GIVEN an archived change whose review record has no `covers`
- WHEN `wm show <change>` runs
- THEN the review is shown as covering every item, and nothing is reported missing

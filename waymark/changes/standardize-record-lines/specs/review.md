# Review

## Modified requirements

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

## Removed requirements

### Requirement: No review tag on items
Reason: The format 2 migration removes every `review:` tag from items and turns the review records under items into `(note)` records, in active and archived changes alike, so no change carries them any more. A tag left by hand is reported like any other text that doesn't belong on an item line.

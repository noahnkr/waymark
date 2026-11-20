# Review

## MODIFIED Requirements

### Requirement: Review recorded in the task list
`wm` SHALL write the review of a change as a `(review)` or `(self-review)` record in the `## Log` section at the end of the change's task list, creating the section if needed. It SHALL write each finding under its record as a sub-line with a severity in brackets (`[critical]`, `[warning]` or `[suggestion]`), its place in backticks, and a text, and then each detail as a sub-line without a severity. A sub-line under a review that starts with a severity in brackets SHALL be read as a finding, one that starts with a severity without brackets SHALL be reported as a finding written without them, and any other SHALL be read as a detail. It SHALL refuse a `pass` verdict, or a self-review, that comes with a critical finding.

#### Scenario: Self-review with a finding
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --finding "warning: src/a.py:12: <text>"`
- THEN the task list ends with a `## Log` section holding a `(self-review)` record with the summary and, under it, ``- [warning] `src/a.py:12`: <text>``

#### Scenario: Self-review with a finding and details
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "every criterion holds" --finding "suggestion: src/a.py: name the constant" --detail "pytest passes" --detail "wm check is healthy"`
- THEN under the `(self-review)` record come ``- [suggestion] `src/a.py`: name the constant``, then `- pytest passes`, then `- wm check is healthy`

#### Scenario: Pass with a critical finding
- GIVEN a change waiting for an independent review
- WHEN a `pass` verdict comes with a `critical` finding
- THEN it is refused with the reason, and nothing is written

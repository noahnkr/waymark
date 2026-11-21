# Agent results

## ADDED Requirements

### Requirement: Details from an agent's ending
When an implementer's or reviewer's message holds lines `DETAIL: <text>` before its two ending lines, `wm` SHALL write each one, in order, as a detail under the record it writes from the ending: the `(note)`, `(blocked)` or `(gap)` of an implementer, or the `(review)` of a reviewer, after its findings. An implementer's `done` ending SHALL write its `(ticked)` record without details.

#### Scenario: Reviewer's details
- GIVEN a change with every item ticked, waiting for an independent review
- WHEN its reviewer ends with `DETAIL: pytest passes`, `DETAIL: wm check is healthy`, `CHANGE: <change>` and `VERDICT: pass: every criterion holds`
- THEN the `(review)` record by `reviewer` has the details `pytest passes` and `wm check is healthy` under it

#### Scenario: Implementer's details
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer ends with `DETAIL: the parser is done`, `ITEM: <change> 1.1` and `RESULT: partial: half built`
- THEN the `(note)` record for item 1.1 by `implementer` has the detail `the parser is done` under it

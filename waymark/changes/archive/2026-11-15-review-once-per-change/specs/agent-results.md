# Agent results

## Purpose

How `wm` records the result of an implementer or reviewer from the agent's own words: its ending, the lines `ITEM: <change> <item>` then `RESULT: …` for an implementer, or `CHANGE: <change>` then `VERDICT: …` for a reviewer, whether the agent ends with a final message or hands its report back through its tool.

## MODIFIED Requirements

### Requirement: Ending recorded from a handed-back report
When an implementer or reviewer hands its report back through its agent tool instead of a final message, `wm` SHALL record the ending from the report's text exactly as from a final message.

#### Scenario: Implementer in the background
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer, running in the background, hands back a report ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`

#### Scenario: Reviewer in the background
- GIVEN a change with every item ticked, waiting for an independent review
- WHEN its reviewer hands back a report ending in `CHANGE: <change>` and `VERDICT: pass: <reasons>`
- THEN a `(review)` line with the reviewer's own reasons is written in the change's `## Review` section

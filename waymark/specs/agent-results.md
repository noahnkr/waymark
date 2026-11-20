# Agent results

## Purpose

How `wm` records the result of an implementer or reviewer from the agent's own words: its ending, the lines `ITEM: <change> <item>` then `RESULT: …` for an implementer, or `CHANGE: <change>` then `VERDICT: …` for a reviewer, whether the agent ends with a final message or hands its report back through its tool.

## Requirements

### Requirement: Ending recorded from a final message
When an implementer or reviewer stops and its final message ends with its two ending lines, `wm` SHALL record what they report: a tick, a blocker, a spec gap, a note or a review record. A record written from an agent's ending SHALL be written `by implementer` or `by reviewer`.

#### Scenario: Implementer done in the foreground
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`, and the Log ends with `<date> (ticked) 1.1 by implementer`

#### Scenario: Implementer partly done
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: partial: <note>`
- THEN item 1.1 is not ticked, and the change's Log ends with `<date> (note) 1.1 by implementer: partial: <note>`

### Requirement: Ending recorded from a handed-back report
When an implementer or reviewer hands its report back through its agent tool instead of a final message, `wm` SHALL record the ending from the report's text exactly as from a final message.

#### Scenario: Implementer in the background
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer, running in the background, hands back a report ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`, and the Log ends with `<date> (ticked) 1.1 by implementer`

#### Scenario: Reviewer in the background
- GIVEN a change with every item ticked, waiting for an independent review
- WHEN its reviewer hands back a report ending in `CHANGE: <change>` and `VERDICT: pass: <reasons>`
- THEN a `(review)` record by `reviewer` with the reviewer's own reasons is written in the change's `## Log` section

### Requirement: Missing ending refused
When a final message or a handed-back report lacks the two ending lines, `wm` SHALL refuse it with the reason, so the agent ends again with them. After a second attempt without them, `wm` SHALL let the agent finish and tell the planner to record the result with the `wm` commands.

#### Scenario: Report without an ending
- GIVEN an implementer running in the background
- WHEN it hands back a report without the `ITEM:` and `RESULT:` lines
- THEN the handback is refused with a reason that names the two lines, and nothing is recorded

### Requirement: Recorded once
An agent's ending SHALL be recorded once. When an agent stops after its handed-back report was recorded, the stop SHALL be allowed without asking for the ending again.

#### Scenario: Stop after a recorded handback
- GIVEN an implementer whose handed-back report ticked item 1.1
- WHEN the agent stops with closing text that has no ending lines
- THEN the stop is allowed, nothing more is recorded, and the agent is not asked for its ending

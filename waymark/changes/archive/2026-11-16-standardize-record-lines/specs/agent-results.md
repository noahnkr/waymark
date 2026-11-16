# Agent results

## Modified requirements

### Requirement: Ending recorded from a final message
When an implementer or reviewer stops and its final message ends with its two ending lines, `wm` SHALL record what they report: a tick, a blocker, a spec gap, a note or a review record. A record written from an agent's ending SHALL be written `by wm-implementer` or `by wm-reviewer`.

#### Scenario: Implementer done in the foreground
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`

#### Scenario: Implementer partly done
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: partial: <note>`
- THEN item 1.1 is not ticked, and has a record `(note) <date> by wm-implementer: partial: <note>` under it

### Requirement: Ending recorded from a handed-back report
When an implementer or reviewer hands its report back through its agent tool instead of a final message, `wm` SHALL record the ending from the report's text exactly as from a final message.

#### Scenario: Implementer in the background
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer, running in the background, hands back a report ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`

#### Scenario: Reviewer in the background
- GIVEN a change with every item ticked, waiting for an independent review
- WHEN its reviewer hands back a report ending in `CHANGE: <change>` and `VERDICT: pass: <reasons>`
- THEN a `(review)` record by `wm-reviewer` with the reviewer's own reasons is written in the change's `## Log` section

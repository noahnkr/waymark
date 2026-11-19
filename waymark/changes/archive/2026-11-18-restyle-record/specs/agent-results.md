# Agent results

## MODIFIED Requirements

### Requirement: Ending recorded from a final message
When an implementer or reviewer stops and its final message ends with its two ending lines, `wm` SHALL record what they report: a tick, a blocker, a spec gap, a note or a review record. A record written from an agent's ending SHALL be written `by wm-implementer` or `by wm-reviewer`.

#### Scenario: Implementer done in the foreground
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: done: <note>`
- THEN item 1.1 is ticked, without anyone running `wm tick`

#### Scenario: Implementer partly done
- GIVEN an accepted change with item 1.1 not ticked
- WHEN its implementer stops with a final message ending in `ITEM: <change> 1.1` and `RESULT: partial: <note>`
- THEN item 1.1 is not ticked, and has a record `<date> (note) by wm-implementer: partial: <note>` under it

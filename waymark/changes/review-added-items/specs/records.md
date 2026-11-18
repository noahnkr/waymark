# Records

## MODIFIED Requirements

### Requirement: Who wrote a record
A record SHALL name who wrote it: the git user for a command run in the session, `wm-implementer` or `wm-reviewer` for an agent's ending, or the value of `--by` when a command is given one. Every command that writes a record SHALL accept `--by <who>`. When no git user is set and no `--by` is given, the record SHALL be written without the `by` part. `wm accept` SHALL still refuse without a git user, as before.

#### Scenario: Reviewer's verdict
- GIVEN a change with items 1.1 and 1.2, waiting for an independent review
- WHEN its reviewer ends with `CHANGE: <change>` and `VERDICT: pass: <reasons>` on 2026-11-20
- THEN the change's Log holds `(review) 2026-11-20 pass covers 1.1 1.2 by wm-reviewer: <reasons>`

#### Scenario: Explicit author
- GIVEN an accepted change with items 1.1 and 1.2, every item ticked, at review level `self`
- WHEN the planner runs `wm review <change> --self "<summary>" --by "Ada and Grace"`
- THEN the self-review record reads `(self-review) <date> covers 1.1 1.2 by Ada and Grace: <summary>`

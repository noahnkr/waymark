# Records

## ADDED Requirements

### Requirement: Details under a record
`wm note`, `wm block`, `wm gap`, `wm resolve`, `wm review --self`, `wm verdict` and `wm revise` SHALL take a repeatable `--detail "<text>"`, and SHALL write each detail as a sub-bullet `  - <text>` under the record, in the order given, after its findings when it has any. The record's text SHALL still be required. A detail SHALL be one line, and SHALL NOT have a finding's shape: a severity in brackets, or a severity word followed by `:` or by a place in backticks. Other text that starts with a severity word, such as `warning signs remain`, SHALL be a detail. `wm show <change>`, in text and JSON, the implement pack's notes from earlier work, the review pack's earlier reviews and `wm pr` SHALL show each record's details under it. In an active change, `wm check` SHALL report a sub-bullet under a record of another kind as an error.

#### Scenario: Note with details
- GIVEN an accepted change with item 1.2 not ticked, and a git user named Ada
- WHEN the planner runs `wm note <change> 1.2 "partly built" --detail "the parser is done" --detail "the CLI flag is not"` on 2026-11-20
- THEN the Log ends with `2026-11-20 (note) 1.2 by planner for Ada: partly built`, then `  - the parser is done`, then `  - the CLI flag is not`

#### Scenario: Details in the views
- GIVEN an accepted change whose Log holds a `(note)` record for item 1.2 with the details `the parser is done` and `the CLI flag is not`
- WHEN the planner runs `wm show <change> --json`
- THEN item 1.2's note has `"details": ["the parser is done", "the CLI flag is not"]`

#### Scenario: Detail that looks like a finding
- GIVEN an accepted change with item 1.2 not ticked
- WHEN the planner runs `wm note <change> 1.2 "<text>" --detail "[warning] not a finding"`
- THEN it is refused with a reason that says a detail doesn't start with a severity in brackets, and nothing is written

#### Scenario: Detail with a finding's shape but no brackets
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --detail "warning: the retry is slow"`
- THEN it is refused with a reason that says the detail has a finding's shape, and nothing is written

#### Scenario: Detail that starts with a severity word
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --detail "warning signs remain"`
- THEN the detail is written under the `(self-review)` record, and `wm check` reports nothing about it

#### Scenario: Sub-bullet under a record without details
- GIVEN an active change whose Log holds `2026-11-20 (ticked) 1.1 by Ada` with the line `  - extra` under it
- WHEN `wm check` runs
- THEN it reports an error on that line that names the kinds of record that take details

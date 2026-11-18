# Terminal output

## Purpose

How `wm`'s text output looks on a terminal and away from one: when it carries color, when it falls back to ASCII, and when its prose is wrapped. JSON output is described with each command.

## ADDED Requirements

### Requirement: Color on a terminal
`wm`'s text output SHALL carry color only when it goes to a terminal and `TERM` isn't `dumb`, or when `FORCE_COLOR` is set to a value other than empty or `0`. When `NO_COLOR` is set, the output SHALL carry no color, whatever else is set. JSON output SHALL never carry color.

#### Scenario: Piped output
- GIVEN no `FORCE_COLOR` or `NO_COLOR` in the environment
- WHEN `wm status` runs with its output piped to a file
- THEN the file holds no escape sequences

#### Scenario: Forced color
- GIVEN `FORCE_COLOR=1` in the environment
- WHEN `wm status` runs with its output piped to a file
- THEN the file holds color escape sequences

#### Scenario: NO_COLOR wins
- GIVEN `FORCE_COLOR=1` and `NO_COLOR=1` in the environment
- WHEN `wm status` runs on a terminal
- THEN the output holds no escape sequences

#### Scenario: JSON
- GIVEN `FORCE_COLOR=1` in the environment
- WHEN `wm status --json` runs
- THEN the output holds no escape sequences

### Requirement: ASCII on consoles without the glyphs
When the output's encoding can't show every glyph `wm` uses, every glyph SHALL be replaced by its ASCII stand-in, and the layout SHALL stay the same.

#### Scenario: Legacy console
- GIVEN output whose encoding is `cp437`
- WHEN `wm show <change>` runs for a change with two items
- THEN the output holds only characters `cp437` can encode, and its items are drawn with ASCII tree lines

### Requirement: Prose wrapped on a terminal
On a terminal, the prose in `wm show`, `wm inbox` and `wm doctor` SHALL be wrapped at word boundaries to the terminal's width, at least 60 and at most 100 columns, each wrapped line keeping its paragraph's indent; a word longer than the width SHALL be left whole. Output that doesn't go to a terminal SHALL NOT be wrapped.

#### Scenario: Narrow terminal
- GIVEN a terminal 80 columns wide, and a change whose Why is one paragraph of 300 characters
- WHEN `wm show <change>` runs
- THEN no line of the Why is longer than 80 columns, each line starts with the paragraph's indent, and no word is split

#### Scenario: Piped
- GIVEN the same change
- WHEN `wm show <change>` runs with its output piped to a file
- THEN the Why is one line, as written

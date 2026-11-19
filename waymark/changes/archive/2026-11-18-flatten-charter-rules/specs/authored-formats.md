# Authored formats

## MODIFIED Requirements

### Requirement: Glossary as a list
The charter's glossary SHALL be a list of `- **<term>**: <meaning>` lines. `wm check` SHALL report a glossary line in another form as an error that shows the form.

#### Scenario: Old glossary line
- GIVEN a charter whose glossary has the line `Record: everything in waymark/`
- WHEN `wm check` runs
- THEN it reports an error that shows the form `- **<term>**: <meaning>`

### Requirement: Numbered goals, constraints and rules
The charter's Goals, Constraints and Rules SHALL be numbered lists, `1. <text>`, numbered from 1 without gaps; Rules MAY be empty. `wm check` SHALL report a line in another form, a heading under Rules included, or a number out of order, with the form expected.

#### Scenario: Bulleted goal
- GIVEN a charter whose Goals hold the line `- Answers in one step.`
- WHEN `wm check` runs
- THEN it reports an error on that line that shows the form `1. <text>`

#### Scenario: Step heading under Rules
- GIVEN a charter whose Rules hold the heading `### Apply` and the line `1. Run the full checks.`
- WHEN `wm check` runs
- THEN it reports an error on the heading that shows the form `1. <text>`

#### Scenario: No rules
- GIVEN a charter whose Rules section holds only a comment
- WHEN `wm check` runs
- THEN it reports nothing about the Rules

## RENAMED Requirements

- **From:** Numbered goals and constraints
- **To:** Numbered goals, constraints and rules

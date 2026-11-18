# Step guidance

## ADDED Requirements

### Requirement: Project rules at every step
Every `wm instructions` output, for every step, SHALL give the charter's Rules whole, the same at each step. The text output SHALL show them as "Project rules", and the JSON output SHALL hold them as `rules`, a string; with no rules, the text output SHALL leave the heading out and `rules` SHALL be empty.

#### Scenario: Same rules at two steps
- GIVEN a charter whose Rules hold `1. Run the full checks.` and `2. Docs follow the house style.`
- WHEN the planner runs `wm instructions --change <change> --json` at the specs step, and again at the apply step
- THEN `rules` holds both rules both times

#### Scenario: No rules
- GIVEN a charter whose Rules section holds only a comment
- WHEN the planner runs `wm instructions explore`
- THEN the text output has no "Project rules" heading

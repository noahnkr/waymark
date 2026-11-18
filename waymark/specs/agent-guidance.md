# Agent guidance

## Purpose

What `wm` gives the agents that build and review a change, beyond the record itself: the rubric a review grades its findings by, and the rules that tell an implementer when to stop.

## Requirements

### Requirement: Severity rubric
`wm context --for review`, and `wm instructions` at a change's review step, SHALL give one severity rubric, the same in both:
- **critical:** a criterion or scenario doesn't hold, the code does what a requirement forbids, or a check fails;
- **warning:** everything holds, but an edge is untested, a requirement is met only by accident, or a likely next change would break it;
- **suggestion:** clarity, naming or duplication that no user would notice;
- when a finding could be either of two severities, it takes the higher, and every critical finding names the item to rebuild.

The text output SHALL show it as "Severity rubric", and the JSON output SHALL hold it as `severity_rubric`, a list of strings.

#### Scenario: Review pack
- GIVEN a change whose items are all ticked
- WHEN the reviewer runs `wm context <change> --for review --json`
- THEN `severity_rubric` says a finding is critical when a criterion or scenario doesn't hold

#### Scenario: Self-review
- GIVEN a change at its review step with review level self
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN `severity_rubric` holds the same rubric as the review pack

### Requirement: Stopping rules
`wm context --for implement` SHALL give the implementer the rules for when to stop, each with the result it ends with:
- the record leaves a choice open, or two parts of it disagree: `spec-gap`, naming what is missing;
- a check fails for a reason outside the item, or the item needs a file or repo outside its scope: `blocked`, naming the cause;
- the same check still fails after three attempts at it: `partial`, saying what was tried;
- other work turns up that the item doesn't ask for: it is left undone and named in a note, and the item is finished as asked.

The text output SHALL show them as "When to stop", and the JSON output SHALL hold them as `stopping_rules`, a list of strings.

#### Scenario: Implement pack
- GIVEN an accepted change whose item 1.1 is next
- WHEN the implementer runs `wm context <change> 1.1 --for implement --json`
- THEN `stopping_rules` holds a rule that ends with `partial` after three attempts at the same failing check

### Requirement: Background in the packs
`wm context --for implement` and `wm context --for review` SHALL hold, for each spec the change has a delta for, the spec's Background as it will read once the change is archived: the delta's Background when the delta has one, otherwise the spec's. A spec with neither SHALL be left out. The text and JSON outputs SHALL hold the same Backgrounds.

#### Scenario: Background of a touched spec
- GIVEN an accepted change with a delta for `lead-nurture` and none for `ats`, where both specs have a Background
- WHEN the planner runs `wm context --for implement <change> 1.1 --json`
- THEN the pack holds `lead-nurture`'s Background and not `ats`'s

#### Scenario: Background from the delta
- GIVEN an accepted change whose delta for `lead-nurture` has a Background that differs from the spec's
- WHEN the planner runs `wm context --for review <change>`
- THEN the pack shows the delta's Background for `lead-nurture`, and not the spec's

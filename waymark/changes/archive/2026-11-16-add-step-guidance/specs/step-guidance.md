# Step guidance

## Purpose

What `wm instructions` gives the planner at each step beyond the next step itself: the checklist for a drafting step, and the rules every skill shares.

## ADDED Requirements

### Requirement: Checklist per drafting step
For the steps propose, specs, design and tasks, `wm instructions` SHALL give a checklist: what must hold in the drafted file before the planner moves on. Each check SHALL say whether `wm check` enforces it. The text output SHALL show the checklist after "What to do", and the JSON output SHALL hold it as `checklist`, a list of objects with `text` and `enforced`. The other steps SHALL give an empty checklist.

#### Scenario: Specs checklist
- GIVEN a change whose next step is specs
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN `checklist` holds a check that every requirement says SHALL, marked enforced, and a check that each THEN can be checked by someone who didn't write it, marked not enforced

#### Scenario: Apply has no checklist
- GIVEN an accepted change whose next step applies an item
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN `checklist` is empty

### Requirement: Shared rules
Every `wm instructions` output, for every step, SHALL give the rules every skill shares, the same list each time:
- only the human accepts a change, or archives one past a missing review;
- only `wm` writes records and ticks items;
- the living specs are changed only by archiving or syncing a change;
- the record is the source of truth: what it doesn't say is asked of the human or recorded as a gap, never guessed;
- nothing is pushed, opened as a pull request or merged without the human's yes in the session.

The text output SHALL show them as "Shared rules", and the JSON output SHALL hold them as `shared_rules`, a list of strings.

#### Scenario: Shared rules at every step
- GIVEN one change whose next step is propose and another whose next step is archive
- WHEN the planner runs `wm instructions --change <change> --json` for each
- THEN both outputs hold the same `shared_rules`, and one of them says only the human accepts a change

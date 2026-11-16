# Paths

## Purpose

The routes work takes, sized by what it changes in the specs. Tiny work changes no requirement and needs no change. The short path is a change with no design. The full path is a change with a design.

## ADDED Requirements

### Requirement: Tiny path
Work that adds, changes or removes no requirement MAY be done without a change, once the human agrees in the session. Outside any change, the planner SHALL be able to edit and commit code and docs, and SHALL NOT be able to edit a spec by hand. Tiny work SHALL leave nothing in the record.

#### Scenario: Code edited outside a change
- GIVEN a project with no change in flight
- WHEN the planner edits a source file
- THEN the edit is allowed

#### Scenario: Spec edited outside a change
- GIVEN a project with no change in flight
- WHEN the planner edits a file under the specs
- THEN the edit is refused with the reason that specs change only through a change

#### Scenario: Nothing recorded
- GIVEN a project with no change in flight
- WHEN the planner fixes a typo in a source file and commits it with a conventional message
- THEN `wm status` shows no change in flight, and `wm check` reports the record healthy

### Requirement: Short and full paths
A change's proposal MAY carry the line `Path: short`. A change on the short path SHALL have no design, and its review level SHALL be `self` or `none`; `wm check` SHALL report a design or an `independent` level on the short path as an error. Any other change SHALL be on the full path, and SHALL have a design before its task list.

#### Scenario: Design on the short path
- GIVEN a change whose proposal has `Path: short`
- WHEN it has a design
- THEN `wm check` reports an error that says the short path has no design

#### Scenario: Full path without a design
- GIVEN a change whose proposal has no `Path:` line, with a proposal and deltas
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is the design

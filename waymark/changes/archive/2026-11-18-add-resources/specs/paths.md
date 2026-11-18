# Paths

## MODIFIED Requirements

### Requirement: Tiny path
Work that adds, changes or removes no requirement MAY be done without a change, once the human agrees in the session. Outside any change, the planner SHALL be able to edit and commit code, docs and resources, and SHALL NOT be able to edit a spec by hand. Tiny work SHALL leave no change, record or other note in the record; the resources it edits are its only trace there.

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

#### Scenario: Resource updated as tiny work
- GIVEN a project with no change in flight, and an active resource whose Configuration names a schedule at 05:00
- WHEN the planner changes the schedule to 06:00 and the `- Verified:` date, and commits it with a conventional message
- THEN `wm status` shows no change in flight, and `wm check` reports the record healthy

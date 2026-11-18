# Records

## ADDED Requirements

### Requirement: Finding places relative to the project
When a finding given to `wm review` or `wm verdict` has a place that starts with an absolute path inside the project, `wm` SHALL write that path relative to the project's top folder, with forward slashes, followed by the rest of the place as given. In an atlas, a place inside a code repo registered on this machine SHALL be written as `<repo>/<path>`. A place that starts with any other absolute path SHALL be refused, before anything is written, with a reason that says to give the place relative to the project. A relative path SHALL be written with forward slashes, and a place that isn't a path SHALL be written as given.

#### Scenario: Absolute path inside the project
- GIVEN a change waiting for its self-review, in a project whose top folder is `C:\work\shop`
- WHEN the planner records it with `--finding "warning: C:\work\shop\src\limit.py:12: the limit is not checked"`
- THEN the finding is written as ``- warning `src/limit.py:12`: the limit is not checked``

#### Scenario: Relative path with backslashes
- GIVEN a change waiting for its self-review
- WHEN the planner records it with `--finding "suggestion: src\limit.py: name the constant"`
- THEN the finding is written as ``- suggestion `src/limit.py`: name the constant``

#### Scenario: Code repo of an atlas
- GIVEN an atlas whose code repo `api` is registered on this machine at `/home/sam/api`
- WHEN a reviewer's verdict is recorded with `--finding "warning: /home/sam/api/src/limit.py:12: the limit is not checked"`
- THEN the finding is written as ``- warning `api/src/limit.py:12`: the limit is not checked``

#### Scenario: Absolute path elsewhere
- GIVEN a change waiting for its self-review
- WHEN the planner records it with a finding whose place is an absolute path outside the project and outside every registered code repo
- THEN the review is refused with the reason that the place must be given relative to the project, and the task list is unchanged

# Commits

## MODIFIED Requirements

### Requirement: Commit messages checked in agent commands
In an agent tool with hooks, a `git commit` whose message isn't a conventional commit SHALL be refused before it runs, with the reason and an example. The check SHALL accept the commit types `wm` knows and, when the settings list commit scopes, only those scopes. It SHALL check a message given on the command line, however it is written there, and a message read from a file the command names. A commit whose message can't be seen before it runs, such as one written in an editor, SHALL be allowed.

#### Scenario: Not conventional
- GIVEN a project in an agent tool with hooks
- WHEN the planner runs `git commit -m "wip"`
- THEN the command is refused, and the reason says how to write a conventional commit

#### Scenario: Conventional
- GIVEN a project in an agent tool with hooks
- WHEN the planner runs `git commit -m "fix: accept an empty search query"`
- THEN the command is allowed

#### Scenario: Scope not listed
- GIVEN a project whose settings list the commit scopes `api` and `docs`
- WHEN the planner runs `git commit -m "feat(web): add a share button"`
- THEN the command is refused, and the reason lists `api` and `docs`

#### Scenario: Message from a here-document
- GIVEN a project in an agent tool with hooks
- WHEN the planner runs `git commit` with a message built from a here-document whose first line is `wip`
- THEN the command is refused

#### Scenario: Message written in an editor
- GIVEN a project in an agent tool with hooks
- WHEN the planner runs `git commit` with no message on the command line or in a file
- THEN the command is allowed

# Resources

## Purpose

The as-built facts about things outside the repo that a project depends on, such as the services it talks to, the platforms it runs on, the accounts it signs in with, the datasets it loads and the documents it was built from: how a resource is laid out, what `wm check` holds it to, who edits it, and how it reaches the agents that need it.

## ADDED Requirements

### Requirement: Resource layout
A resource SHALL be a file `resources/<name>.md` in the record, describing one account or one separate deployment of something outside the repo; the environments of one deployment SHALL be described in the same file. It SHALL have a title, the lines `- Kind:`, `- Serves:`, `- Status:` and `- Verified:`, and the sections `## What it is`, `## Access`, `## Interface`, `## Data`, `## Configuration` and `## Verification`, each present even when it holds only `None.`. `- Status:` SHALL be `active` or `retired`, and `- Verified:` a date `YYYY-MM-DD`. `wm check` SHALL report as an error a resource with a section or line missing, or with a status or date in another form.

#### Scenario: Complete resource
- GIVEN a resource with a title, `- Kind: service`, `- Serves: none`, `- Status: active`, `- Verified: 2026-11-17` and all six sections, its Interface holding only `None.`
- WHEN the planner runs `wm check`
- THEN `wm check` reports nothing about the resource

#### Scenario: Missing section
- GIVEN a resource with no `## Data` section
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on the resource that names the Data section

#### Scenario: Date in another form
- GIVEN a resource with `- Verified: last week`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that says the date is written `YYYY-MM-DD`

### Requirement: Resource kinds
A resource's `- Kind:` SHALL be one of `service`, `platform`, `account`, `database`, `dataset` or `document`. `wm check` SHALL report any other kind as an error that lists the six.

#### Scenario: Unknown kind
- GIVEN a resource with `- Kind: repository`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that lists `service`, `platform`, `account`, `database`, `dataset` and `document`

### Requirement: Specs a resource serves
A resource's `- Serves:` line SHALL name the specs the resource serves, separated by commas, or be `none`. `wm check` SHALL report as an error a name that isn't a spec in the record.

#### Scenario: Unknown spec
- GIVEN a record with the specs `search` and `export`, and a resource with `- Serves: search, billing`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that names `billing` and lists the specs

### Requirement: Resources edited by hand
A resource SHALL be edited by hand, not through a change's deltas: the planner SHALL be able to edit, create or remove a resource whether or not a change is in flight, and an implementer SHALL be able to edit, create or remove one while building its item. A reviewer SHALL NOT edit a resource.

#### Scenario: Planner edits outside a change
- GIVEN a project with no change in flight
- WHEN the planner edits a resource
- THEN the edit is allowed

#### Scenario: Implementer edits a resource
- GIVEN an implementer building item 1.2
- WHEN it edits a resource
- THEN the edit is allowed

#### Scenario: Reviewer edits a resource
- GIVEN a reviewer reviewing a change
- WHEN it edits a resource
- THEN the edit is refused with the reason that a reviewer edits nothing

### Requirement: Resource commands
`wm new resource <name> <kind>` SHALL create `resources/<name>.md` from the built-in template, which holds the six sections, the four lines and the rule never to store secrets, with `- Kind:` set to the given kind, `- Serves: none`, `- Status: active` and `- Verified:` set to the day it runs, and SHALL print `Created the resource "<name>".`. It SHALL refuse a name that is already a resource, and a kind that is missing or not one of the six, listing the six. `wm ls resources` SHALL list every resource with its kind, status and the specs it serves, and `wm show <name> --kind resource` SHALL show one resource in full.

#### Scenario: New resource
- GIVEN a record with no resource named `stripe`
- WHEN the planner runs `wm new resource stripe service` on 2026-11-17
- THEN `resources/stripe.md` exists with the six sections and the lines `- Kind: service`, `- Serves: none`, `- Status: active` and `- Verified: 2026-11-17`, `wm` prints `Created the resource "stripe".`, and `wm check` reports nothing about it

#### Scenario: Name taken
- GIVEN a record with a resource named `stripe`
- WHEN the planner runs `wm new resource stripe service`
- THEN `wm` refuses, says the resource already exists, and leaves the file unchanged

#### Scenario: Unknown kind given
- GIVEN a record with no resource named `stripe`
- WHEN the planner runs `wm new resource stripe repository`
- THEN `wm` refuses with a reason that lists `service`, `platform`, `account`, `database`, `dataset` and `document`, and writes no file

#### Scenario: Listing
- GIVEN a record with an active `service` resource `stripe` serving `billing`, and a retired `platform` resource `heroku` serving none
- WHEN the planner runs `wm ls resources`
- THEN the output lists `stripe` with `service`, `active` and `billing`, and `heroku` with `platform`, `retired` and `none`

### Requirement: Resources in context packs
`wm context --for explore` SHALL hold an index of every resource: its name, title, kind, status and the specs it serves. `wm context --for implement` and `wm context --for review` SHALL hold, for each active resource that serves a spec the change has a delta for, its name, its kind, its What it is and Access sections in full, and the headings of the rest of the file, with the command that shows it in full. A retired resource SHALL NOT be in the implement or review pack. The text and JSON outputs SHALL hold the same resources.

#### Scenario: Serving resource in the implement pack
- GIVEN an accepted change with a delta for `billing`, and an active resource `stripe` serving `billing` whose Configuration has the subsections `### dev` and `### prod`
- WHEN the planner runs `wm context --for implement <change> 1.1 --json`
- THEN the pack holds `stripe` with its What it is and Access text, and headings including Configuration, `dev` and `prod`, but not the text under Configuration

#### Scenario: Resource for another spec
- GIVEN an accepted change with a delta for `billing` only, and an active resource `mailgun` serving `notifications`
- WHEN the planner runs `wm context --for implement <change> 1.1`
- THEN the pack doesn't mention `mailgun`

#### Scenario: Retired resource
- GIVEN an accepted change with a delta for `billing`, and a retired resource `heroku` serving `billing`
- WHEN the planner runs `wm context --for review <change>`
- THEN the pack doesn't mention `heroku`

#### Scenario: Explore index
- GIVEN a record with the resources `stripe` (active) and `heroku` (retired)
- WHEN the planner runs `wm context --for explore`
- THEN the pack lists both, each with its kind, status and the specs it serves

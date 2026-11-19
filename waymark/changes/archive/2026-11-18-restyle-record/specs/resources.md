# Resources

## MODIFIED Requirements

### Requirement: Resource layout
A resource SHALL be a file `resources/<name>.md` in the record, describing one account or one separate deployment of something outside the repo; the environments of one deployment SHALL be described in the same file. It SHALL have a title, the lines `- **Kind:**`, `- **Serves:**`, `- **Status:**` and `- **Verified:**`, and the sections `## What it is`, `## Access`, `## Interface`, `## Data`, `## Configuration` and `## Verification`, each present even when it holds only `None.`. `- **Status:**` SHALL be `active` or `retired`, and `- **Verified:**` a date `YYYY-MM-DD`. `wm check` SHALL report as an error a resource with a section or line missing, or with a status or date in another form.

#### Scenario: Complete resource
- GIVEN a resource with a title, `- **Kind:** service`, `- **Serves:** none`, `- **Status:** active`, `- **Verified:** 2026-11-17` and all six sections, its Interface holding only `None.`
- WHEN the planner runs `wm check`
- THEN `wm check` reports nothing about the resource

#### Scenario: Missing section
- GIVEN a resource with no `## Data` section
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on the resource that names the Data section

#### Scenario: Date in another form
- GIVEN a resource with `- **Verified:** last week`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that says the date is written `YYYY-MM-DD`

### Requirement: Resource kinds
A resource's `- **Kind:**` SHALL be one of `service`, `platform`, `account`, `database`, `dataset` or `document`. `wm check` SHALL report any other kind as an error that lists the six.

#### Scenario: Unknown kind
- GIVEN a resource with `- **Kind:** repository`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that lists `service`, `platform`, `account`, `database`, `dataset` and `document`

### Requirement: Specs a resource serves
A resource's `- **Serves:**` line SHALL name the specs the resource serves, separated by commas, or be `none`. `wm check` SHALL report as an error a name that isn't a spec in the record.

#### Scenario: Unknown spec
- GIVEN a record with the specs `search` and `export`, and a resource with `- **Serves:** search, billing`
- WHEN the planner runs `wm check`
- THEN `wm check` reports an error on that line that names `billing` and lists the specs

### Requirement: Resource commands
`wm new resource <name> <kind>` SHALL create `resources/<name>.md` from the built-in template, which holds the six sections, the four lines and the rule never to store secrets, with `- **Kind:**` set to the given kind, `- **Serves:** none`, `- **Status:** active` and `- **Verified:**` set to the day it runs, and SHALL print `Created the resource "<name>".`. It SHALL refuse a name that is already a resource, and a kind that is missing or not one of the six, listing the six. `wm ls resources` SHALL list every resource with its kind, status and the specs it serves, and `wm show <name> --kind resource` SHALL show one resource in full.

#### Scenario: New resource
- GIVEN a record with no resource named `stripe`
- WHEN the planner runs `wm new resource stripe service` on 2026-11-17
- THEN `resources/stripe.md` exists with the six sections and the lines `- **Kind:** service`, `- **Serves:** none`, `- **Status:** active` and `- **Verified:** 2026-11-17`, `wm` prints `Created the resource "stripe".`, and `wm check` reports nothing about it

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

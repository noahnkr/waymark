# Explorations

## Purpose

An exploration: saved thinking on an idea, kept until it is decided. Where an exploration stands, how it ends, through a change or milestone it leads to or by being dropped, and how an ended one leaves the active record for the archive, written each time by the `wm` command that ends it.

## ADDED Requirements

### Requirement: Exploration status
An exploration SHALL say where it stands in a `- Status:` line under its title: `open` while it waits to be decided or built; `led-to` followed by one or more links, separated by commas, to the changes or milestones it led to; or `dropped` when it was weighed and won't be acted on. `wm new exploration` SHALL write `- Status: open`. `wm check` SHALL report a missing status as `missing-status`, any other value, `parked` included, as an unknown status that lists the three, and a `led-to` link that doesn't resolve to a change or milestone in the record.

#### Scenario: New exploration
- WHEN the planner runs `wm new exploration result-paging`
- THEN `explorations/result-paging.md` has the line `- Status: open`, and `wm context --for explore` lists it as open

#### Scenario: Parked is not a status
- GIVEN an active exploration with `- Status: parked`
- WHEN `wm check` runs
- THEN it reports an error on that line that names `open`, `led-to` and `dropped`

#### Scenario: Missing status
- GIVEN an exploration with no `- Status:` line
- WHEN `wm check` runs
- THEN it reports `missing-status`, and the message asks for a `- Status:` line without naming `wm update`

### Requirement: Led-to written by --from
`wm new change <name> --from <exploration>` and `wm new milestone <name> --from <exploration>` SHALL set the active exploration's Status line to `led-to` with a link to the new change's proposal or the new milestone's `milestone.md`, in the same operation that creates it. When the exploration already has a `led-to` status, the new link SHALL be added to the end of the line and the links already there kept. An exploration that isn't active, or is unknown, SHALL be refused, and nothing created.

#### Scenario: Change from an open exploration
- GIVEN the open exploration `result-paging`
- WHEN the planner runs `wm new change add-search-limit --from result-paging`
- THEN the change `add-search-limit` is created, and the exploration's line reads `- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md)`

#### Scenario: A second change from the same exploration
- GIVEN the exploration `result-paging` with `- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md)`
- WHEN the planner runs `wm new change add-page-cursor --from result-paging`
- THEN the exploration's Status line links both `add-search-limit` and `add-page-cursor`, in that order

#### Scenario: Milestone from an exploration
- GIVEN the open exploration `faster-search-ideas`
- WHEN the planner runs `wm new milestone faster-search --from faster-search-ideas`
- THEN the exploration's line reads `- Status: led-to [faster-search](../milestones/faster-search/milestone.md)`

#### Scenario: Unknown exploration
- GIVEN no active exploration named `result-paging`
- WHEN the planner runs `wm new change add-search-limit --from result-paging`
- THEN it is refused with a reason that names `result-paging`, and no change folder is created

### Requirement: Archived with its work
When `wm archive <change>` or `wm close <milestone>` leaves every target on an active exploration's `led-to` line archived or closed, it SHALL move that exploration to `explorations/archive/<date>-<name>.md`, dated the day of the archive, in the same operation, with its links re-aimed from its new place. An exploration with a target still active SHALL stay where it is, with its link to the archived target re-aimed.

#### Scenario: Its only change archived
- GIVEN the exploration `result-paging` led to the change `add-search-limit` alone
- WHEN the human runs `wm archive add-search-limit` on 2026-12-01
- THEN the exploration is at `explorations/archive/2026-12-01-result-paging.md`, its Status line links the archived change, and `wm context --for explore` no longer lists it

#### Scenario: One of two changes archived
- GIVEN the exploration `result-paging` led to the changes `add-search-limit` and `add-page-cursor`
- WHEN the human runs `wm archive add-search-limit`
- THEN the exploration stays in `explorations/`, and its Status line links the archived `add-search-limit` and the active `add-page-cursor`

#### Scenario: Its milestone closed
- GIVEN the exploration `faster-search-ideas` led to the milestone `faster-search`, whose roadmap lines all link archived changes
- WHEN the planner runs `wm close faster-search` on 2026-12-01
- THEN the exploration is at `explorations/archive/2026-12-01-faster-search-ideas.md`, and its Status line links the closed milestone

#### Scenario: Change in a milestone the exploration led to
- GIVEN the exploration `faster-search-ideas` led to the milestone `faster-search`, and `add-cache` is a change on its roadmap
- WHEN the human runs `wm archive add-cache`
- THEN the exploration stays in `explorations/`

### Requirement: Dropping an exploration
`wm exploration drop <exploration> --reason "<why>"` SHALL set an open exploration's status to `dropped`, add the reason as the last paragraph of its `## Conclusion`, and move it to `explorations/archive/<date>-<name>.md`, in one operation. It SHALL refuse an exploration that has led to a change or milestone, saying it ends when its work is archived, and an unknown one, naming the active explorations. A refusal SHALL change nothing.

#### Scenario: Drop an open exploration
- GIVEN the open exploration `result-paging` with an empty Conclusion
- WHEN the planner runs `wm exploration drop result-paging --reason "Results never pass fifty."` on 2026-12-01
- THEN `explorations/archive/2026-12-01-result-paging.md` has `- Status: dropped` and the Conclusion "Results never pass fifty.", and `explorations/result-paging.md` no longer exists

#### Scenario: Conclusion kept
- GIVEN the open exploration `result-paging` whose Conclusion holds "Paging needs a cursor."
- WHEN the planner runs `wm exploration drop result-paging --reason "Results never pass fifty."`
- THEN the archived Conclusion holds "Paging needs a cursor." followed by "Results never pass fifty."

#### Scenario: Drop an exploration that led to a change
- GIVEN the exploration `result-paging` with a `led-to` status
- WHEN the planner runs `wm exploration drop result-paging --reason "Not needed."`
- THEN it is refused with a reason that says the exploration ends when its work is archived, and no file changes

### Requirement: Status lines written only by wm
An agent's edit to an active exploration that adds, changes or removes its `- Status:` line SHALL be refused with a reason that names `--from` and `wm exploration drop`. Edits to the exploration's other lines SHALL be allowed.

#### Scenario: Agent writes led-to by hand
- GIVEN the open exploration `result-paging`
- WHEN the planner edits its Status line to `- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md)`
- THEN the edit is refused with a reason that names `--from` and `wm exploration drop`

#### Scenario: Agent edits the questions
- GIVEN the open exploration `result-paging`
- WHEN the planner adds a line under its `## Questions`
- THEN the edit is allowed

### Requirement: Archived explorations in the views
`wm show <exploration>` SHALL find an archived exploration by its name or its dated file name, and say the day it was archived. `wm ls explorations` SHALL list the active explorations, and with `--archived` the archived ones too, each marked archived. `wm context --for explore` SHALL list only the active explorations.

#### Scenario: Show an archived exploration
- GIVEN the exploration `result-paging` archived on 2026-12-01
- WHEN the planner runs `wm show result-paging`
- THEN it shows the exploration, with its status and "Archived on 2026-12-01"

#### Scenario: List with the archived ones
- GIVEN one active exploration and one archived
- WHEN the planner runs `wm ls explorations --archived`
- THEN both are listed, and the archived one is marked archived

### Requirement: Led-to left active
`wm check` SHALL report as an error an active exploration whose `led-to` targets are all archived or closed, saying it belongs in `explorations/archive/`. Archived explorations SHALL be read as they were written, and SHALL NOT be reported.

#### Scenario: Exploration whose milestone closed
- GIVEN an active exploration whose Status line links only a closed milestone
- WHEN `wm check` runs
- THEN it reports an error on the exploration that names `explorations/archive/`

#### Scenario: Archived exploration with an old status
- GIVEN an archived exploration with `- Status: parked`
- WHEN `wm check` runs
- THEN it reports no problem in that exploration

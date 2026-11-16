# Authored formats

## Purpose

The layouts of what humans and the planner write in the record: the proposal's facts, Impact and Outcome, the charter's glossary, goals, constraints and rule headings, a task item's criteria, verification and build line, a delta's sections, a design's decisions and open questions, a milestone's file, an exploration's status, and the examples the templates carry. What `wm` writes is in the `records` spec.

## ADDED Requirements

### Requirement: Milestone as one file
A milestone SHALL be a folder holding one file, `milestone.md`: a title, then the sections `## Goal`, `## Done when`, `## Non-goals` and `## Roadmap`, in that order. `wm new milestone` SHALL write it so. The list lines under `## Roadmap`, and only those, SHALL be the milestone's roadmap entries. `wm check` SHALL report a `goal.md` or `roadmap.md` in a milestone folder, active or archived, as an error that names `milestone.md`.

#### Scenario: New milestone
- WHEN the planner runs `wm new milestone faster-search`
- THEN the folder `milestones/faster-search` holds only `milestone.md`, with the four sections in order

#### Scenario: Old milestone files
- GIVEN a milestone folder holding `goal.md` and `roadmap.md`
- WHEN `wm check` runs
- THEN it reports an error on each file that names `milestone.md`

#### Scenario: Roadmap ticked at archive
- GIVEN a milestone whose `## Roadmap` links to the change `add-limit`, and whose `## Done when` holds a bullet
- WHEN `add-limit` is archived
- THEN the roadmap line links to the archived change and `wm status` counts it as archived, and the `## Done when` bullet is unchanged and isn't counted as a roadmap entry

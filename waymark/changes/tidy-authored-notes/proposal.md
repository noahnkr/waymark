# Tidy authored notes

Owner: Noah Roberts
Review: independent

## Why

What `wm` writes now has one shape (`standardize-record-lines`). What humans and the planner write is still uneven, and some of it renders badly or is hard to scan:

- the proposal's `Owner:`, `Review:` and `Path:` lines, and the charter's glossary, run together into one paragraph on GitHub;
- a task item's criteria are one long line, and its build tag hides at the end of the title line;
- delta section headings read like prose, and renaming a requirement means removing it and adding it again;
- an exploration's state is guessed from its Conclusion's text.

These are layout changes a migration can make without guessing. This is the second change on the `record-format-and-skills` milestone; the formats that add meaning, which existing content can't be migrated to, follow in `structure-authored-notes`.

## What changes

- **Proposal:** `Owner`, `Review` and `Path` become a bullet list under the title, such as `- Owner: Ada`.
- **Charter:** the glossary is a `- **Term**: meaning` list. Step headings under Rules are capitalized (`### Apply`), and a step with no rules may leave its heading out.
- **Task items:** criteria may be a nested list under `- Criteria:`, one criterion per bullet. The build tag becomes a `- Build: delegate` sub-line instead of a tag at the end of the title.
- **Deltas:** the sections are `## ADDED Requirements`, `## MODIFIED Requirements` and `## REMOVED Requirements`. A new `## RENAMED Requirements` section, with `- From:` and `- To:` lines, renames a requirement without removing and adding it.
- **Exploration:** a `- Status: open|parked|led-to <link>` line under the title says where it stands, and `Parked:` in the Conclusion goes.
- **Record format 3.** `wm update` migrates every change, active and archived, the charter and the explorations to these layouts. `wm` then reads only format 3. `wm check --fix` keeps them in their standard form.
- **Templates, skills and docs** show the new layouts.

## Non-goals

- A structured Impact and Outcome, numbered goals and constraints, settled decisions and open questions in the design, and examples in the templates: the next change, `structure-authored-notes`.
- Merging a milestone's goal and roadmap: `merge-milestone-files`.
- Stable IDs for requirements; names stay their keys.

## Impact

- New spec `authored-formats`: the proposal, charter, task item, delta and exploration layouts, and the format 3 migration.
- Spec `building`: the delegation tag becomes a `Build:` sub-line; the requirements that name the tag are modified.
- **Behavior change for every user, for the changelog:** the record format goes to 3 and `wm update` migrates every change; proposal facts, the glossary, the build tag, delta headings and the exploration's state change form; `RENAMED` is new in deltas.
- Code: `record/` (outline, proposal, charter, tasks, deltas, explorations, layout, templates, fingerprint), `services/` (migrations, instructions, lifecycle), `views/`.
- Assets: `wm-propose`, `wm-update`, `wm-kickoff`, `wm-explore`, `wm-apply`. Docs: concepts, getting started, the README example, the changelog.

# Restyle record

- **Owner:** Noah Roberts
- **Review:** independent

## Why

The record is read most in a pull request, on GitHub's rendered markdown, and in other markdown views. There, a task item, its records and the Log run together as one plain list: a label such as `Criteria:` looks like the start of any sentence, the item's `Build:` line comes last though it says who builds the item, and a review record runs two item lists side by side (`changes 2.2 1.2 3.2 covers 1.1 1.2 …`) that are hard to tell apart. A finding starts with a bare lowercase word (`critical`), which reads like prose rather than a mark `wm` wrote. And a decision's options may be one line split on `;` or "or", which the check counts by splitting on any "or", so `- Options: cut before or after sorting` passes as two options.

This record is Waymark's only instance, so the layouts can change in place: the readers learn only the new layouts, and the archived files are rewritten once.

## What changes

- **Labels are bold**, colon inside: `- **Owner:** Ada`, `- **Criteria:**`. This covers every label line in the record, whether a human or `wm` writes it: the proposal's facts, Impact and Outcome; a task item's Build, Repo, Criteria and Verify; a decision's Status, Decided by, Options, Choice and Why; a delta's From, To and Reason; an exploration's Status; a resource's Kind, Serves, Status and Verified. The charter's glossary takes the same form: `- **<term>:** <meaning>`.
- `wm check` reports a known label written plain, showing the bold form, and `wm check --fix` makes it bold.
- **Every task item has a Build line**, `- **Build:** planner` or `- **Build:** delegate`, and an item's lines come in the order Build, Repo, Criteria, Verify. `wm check` reports a missing Build line and a line out of order, and `wm check --fix` puts the lines in order.
- **A decision's options are a nested list**, one option per bullet, at least two; a one-line `Options:` is reported.
- **A record starts with its date**, then its kind: `<date> (<kind>) [<args>] [by <who>]: <text>`, so the dates line up and a Log reads as a timeline.
- **Item lists in records are separated by commas**, and two lists in one record by `; `: `<date> (accepted) fingerprint <digest> items 1.1, 1.2 by Ada` and `<date> (review) changes 1.2, 2.2; covers 1.1, 1.2, 2.2 by wm-reviewer: …`. Records keep their parentheses and the word `fingerprint`.
- **A finding's severity is in brackets**: ``- [critical] `src/a.py:12`: the limit is not checked``.
- The templates, the skills, the agent definitions and the docs use the new layouts.
- This record moves to the new layouts: the active files by `wm check --fix` and by hand, and the archived changes, milestones and explorations once, by a script that is run and not committed. The record stays at format 1.

## Non-goals

- Moving item records into the Log: that is the next change, which comes after this one.
- Reading the old layouts: `wm` reads only the new ones, and no command migrates a record.
- Bold or other styling in what `wm` prints to a terminal; only the files change.
- Restyling a spec's own text: requirement and scenario headings and the GIVEN, WHEN and THEN steps stay as they are.
- Keeping the archived fingerprints valid: they were taken over the old layout, and archived changes are never checked.

## Impact

- **Specs:** `acceptance`, `agent-results`, `authored-formats`, `branches`, `building`, `explorations`, `formatting`, `milestones`, `paths`, `records`, `resources`, `review` (all modified)
- **User-visible:**
  - the record's label lines are bold, colon inside, and the glossary's terms too
  - every task item has a `Build:` line, `planner` or `delegate`, first among its lines
  - a decision's options are a nested list
  - every record, in a change and in a milestone's Log, starts with its date: `<date> (<kind>) …`
  - item lists in records are separated by commas, and a review's two lists by `; `
  - a finding's severity is written in brackets, `[critical]`
  - `wm check` reports a plain label, a missing Build line, an item's lines out of order and a one-line Options; `wm check --fix` fixes the first and third
- **Code:** `record/` (the artifact readers, `markdown/outline.py`, `evidence/records.py` and `evidence.py`, `writing/layout.py` and the templates), `services/` (check, setup, lifecycle, context, instructions), `hooks/decide.py`, the skills and agent definitions in `assets/`, the tests, the docs and the CHANGELOG, and this record's active and archived files

## Outcome

- **Built:** Every label in the record is bold (`- **<Label>:**`), read only in that form and reported otherwise. Every item has a Build line (planner or delegate) first, the item order is checked, and `wm check --fix` bolds labels and reorders items. Options are counted only as nested bullets. Records start with their date and use comma-separated item lists, and findings put their severity in brackets. The active record and the archive were converted; the skills, agents, docs and CHANGELOG show the new layouts.
- **Differs:** `wm show` and the context packs still print records and labels in the old shapes (the reviewer's two warnings, left for a follow-up). `wm check --fix` doesn't bold labels in the charter, which reads none. The reviewer agent definition was updated too, though only the implementer was named.

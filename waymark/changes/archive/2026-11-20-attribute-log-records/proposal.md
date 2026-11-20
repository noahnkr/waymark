# Attribute log records

- **Owner:** Noah Roberts
- **Review:** independent

## Why

A change's Log is its history, but it doesn't say who did what:

- **Who wrote it.** Every record written in a session names the git user. A note or a self-review the planner wrote reads `by Ada`, just like Ada's acceptance. In a team, the record credits a person with words they didn't write. Agents' records say `by wm-implementer` and `by wm-reviewer`, which don't match the roles a Build line names.
- **What is missing.** A tick writes no record, so the Log doesn't say when an item was finished, or by whom. That matters most for a `human` item, where the tick is the human's confirmation. Archiving writes nothing into the change's own Log, although it is the human's second approval. And when an accepted change is edited and accepted again, the Log shows two `(accepted)` records with different fingerprints and nothing between them to say what changed or why.
- **Stale scenarios.** In the `records` spec, two scenarios under "One record shape" still put a record under its item instead of in the Log.

## What changes

- **Who a record names**, by what the record is:
  - the human's acts name the git user (`by Ada`): `(accepted)`, `(override)`, `(resolved)`, `(archived)`, and `(ticked)` for a `human` item;
  - what the planner writes names the planner and the human it works with (`by planner for Ada`): `(note)`, `(blocked)`, `(gap)`, `(reopened)`, `(self-review)`, `(synced)`, `(revised)`, `(ticked)` for any other item, and a milestone's roadmap records;
  - records from an agent's ending name its role, `by implementer` or `by reviewer`, and an implementer's own `wm note` must say `--by implementer`;
  - `--by` still names someone else when given.
- **Ticks recorded.** `wm tick` writes `<date> (ticked) <item> by <who>` into the Log, and so does an implementer's `done` ending. A tick still keeps the acceptance.
- **Archive recorded.** `wm archive` writes `<date> (archived) by <who>` into the change's Log before it moves the change.
- **Revisions recorded.** A new command, `wm revise <change> "<why>"`, with `--parts` naming the parts it changed (item numbers, `proposal`, `design` or `specs/<area>`), writes `<date> (revised) [<part>, <part>...] by <who>: <why>`. `wm accept` refuses to accept a change again while no `(revised)` record follows its last `(accepted)` record, and names `wm revise`. The `wm-update` skill runs `wm revise` after each confirmed edit, and when it adds an item.
- **Stale scenarios.** The two scenarios under "One record shape" put their record in the Log, naming the item.
- **Old records** are left as they were written.
- The skills, the agent definitions and the docs say who records name, and show the new records.

## Non-goals

- Writing a record, or a part of one, as a list. That comes in a later change.
- Rewriting records already in the record, in active or archived changes.
- `wm` checking that a `(revised)` record says truly what changed, or naming the changed parts by itself.
- Telling whether the human or the planner typed a command. The record's kind decides, and `--by` corrects it.

## Impact

- **Specs:**
  - `records` (modified)
  - `acceptance` (modified)
  - `agent-results` (modified)
  - `milestones` (modified)
  - `review` (modified)
  - `archiving` (modified)
- **User-visible:**
  - Records name `planner for <name>`, `implementer` or `reviewer`, or the human, by their kind.
  - `wm tick` and `wm archive` write records, and `wm tick` takes `--by`.
  - A new command, `wm revise`, and a `(revised)` record; `wm accept` refuses to accept a change again without one.
  - An implementer's `wm note` without `--by implementer` is refused.
- **Code:** the record kinds and authorship in `record/evidence/records.py`, the commands in `services/lifecycle.py`, `services/roadmap.py` and `services/setup.py`, the CLI in `cli.py`, the agents' endings and the command rules in `hooks/decide.py`, the skills and agent definitions in `assets/`, the docs and CHANGELOG.

## Outcome

- **Built:** Records name who wrote them by their kind: the human's acts name the git user, what the planner writes names planner for the git user, and an agent's ending names implementer or reviewer. --by overrides it on every writing command, wm new change included. wm tick writes (ticked) and requires a date, wm archive ends the change's own Log with (archived), and the new wm revise writes (revised), without which wm accept refuses a second acceptance. An implementer's wm note must name only implementer. The two stale records scenarios are fixed, old records keep their names, and the skills, agent definitions, docs and CHANGELOG match.
- **Differs:** The first independent review asked for changes to 1.2, 1.3, 2.1 and 2.2 (no --by on wm new change, undated ticks in the README evidence, one wm revise instead of one per edit, two stale doc examples); all were fixed with its two warnings, and the second review passed. tick requires its date, as the design said, so every caller was updated. A verdict recorded in the session without --by names the planner, under the design's every-other-kind rule. The author function keeps the name who_for rather than author, which is the open suggestion.

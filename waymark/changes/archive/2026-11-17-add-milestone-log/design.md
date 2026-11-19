# Add milestone log: design

## Context

- `record/records.py` holds every kind of record in `KINDS`, each with a `Grammar` for its arguments and a `Level`: `ITEM`, `CHANGE` or `BOTH`. No grammar takes a change's name, and no level is a milestone.
- `record/milestones.py` reads `milestone.md`: the Goal sections and the roadmap entries, each with its link target and line index. It has `link_change` for `wm new change --milestone`. Its sections are Goal, Done when, Non-goals and Roadmap; nothing reads a `## Log`.
- `services/lifecycle.archive` ticks and relinks a member's roadmap line with `tick_roadmap_lines` and `rewrite_links` (`record/moves.py`). `close_milestone` refuses active and missing members, and lets planned lines through, naming them as never proposed.
- `record/evidence.py` names the evidence in a task list: ticks, item records and Log lines. `hooks/decide._edit` refuses an agent's edit that changes it, using `evidence_changes`. A file that isn't a task list has no evidence.
- `services/setup.create_change` links the roadmap in the same transaction as the proposal.
- The `wm-explore` skill starts a milestone and drafts its roadmap lines by hand, `wm-propose` drafts member changes, and `wm-archive` step 6 says to link the archived change in the roadmap by hand, which `wm archive` already does.

## Approach

1. **Record kinds.** `records.py` gains the kinds `ADDED`, `DROPPED`, `MOVED`, `PROPOSED` and `ARCHIVED`, at a new `Level.MILESTONE`. Two grammars: `CHANGE_NAME`, one change name (`added`, `dropped`, `proposed`, `archived`); `MOVE`, a change name then `after <name>` or `first` (`moved`). `added` and `dropped` have text, the description and the reason; the others have none. `Record` gains `change` and `after` fields, the latter empty for `first`. Render and parse round-trip as for the other kinds.
2. **The milestone's Log.** `milestones.py` reads an optional `## Log` section after `## Roadmap`, as the records in it, and reports `log-section-last` when another section follows it. The milestone template is unchanged. A helper `append_milestone_log(doc, line)` returns the text with the record added at the end of the Log, creating `## Log` after the last section when there is none, keeping line endings.
3. **`wm roadmap`.** A new `services/roadmap.py` holds `add`, `drop` and `move`. Each opens the record for writing, finds the active milestone, edits the roadmap's lines by text with the file's line endings kept, appends its record to the Log, and writes both in one transaction:
   - `add` refuses an invalid name, or a name already on the roadmap, linked or planned, and adds `- <change>: <description>` after the last roadmap line;
   - `drop` refuses a change not on the roadmap, or one active in `record.changes` whose proposal names this milestone, and removes the line;
   - `move` refuses a change or an `--after` target not on the roadmap, or `--after` itself, and moves the line.
   `cli.py` adds `wm roadmap {add,drop,move}`, with `--reason` required on `drop`, and `--after` and `--first` as a required, mutually exclusive pair on `move`. Every command takes `--by`.
4. **The other writers.** `create_change` appends `(proposed)` in the transaction it already has. `archive` appends `(archived)` to the milestone of the change's proposal, in the same pass that ticks and relinks the roadmap line, when the milestone is active.
5. **Evidence.** `evidence.py` names a milestone's evidence: each roadmap list line, and each line of its `## Log`. `evidence_changes` then covers `milestone.md`, so the hook refuses an agent's edit that changes either. The hook's refusal for a milestone names `wm roadmap add`, `drop` and `move`.
6. **`wm close`.** `close_milestone` also refuses planned lines, naming them and `wm roadmap drop`.
7. **Skills and docs.** `wm-explore` starts a milestone with `wm new milestone`, drafts its Goal sections, and adds roadmap lines with `wm roadmap add`. `wm-propose` keeps using `wm new change --milestone`. `wm-archive` step 6 no longer links by hand, and says to drop or add lines with `wm roadmap` when the path changed. `docs/record.md`, `docs/concepts.md` and `docs/cli.md` (generated) describe it, and the changelog gets its line.

## Decisions

### Decision: How hand edits are refused
- **Status:** decided
- **Decided by:** human
- **Options:** hooks refuse agents' edits to roadmap lines and the Log, as evidence; the same plus `wm check` replaying the Log against the roadmap
- **Choice:** hooks only, as evidence
- **Why:** it matches how ticks and records in a task list are guarded, and a replay would need every existing roadmap to start from a Log that lists its lines

### Decision: How `move` names the position
- **Status:** decided
- **Decided by:** human
- **Options:** `--after <change>` or `--first`; a position number
- **Choice:** `--after <change>` or `--first`
- **Why:** names stay meaningful as other lines move, and the record reads as a sentence

### Decision: Dropping an active member change
- **Status:** decided
- **Decided by:** human
- **Options:** refuse it until its proposal no longer names the milestone; allow it and let `wm check` report the change
- **Choice:** refuse it
- **Why:** dropping it would leave a member the roadmap no longer lists; taking the `- Milestone:` line off the proposal first is a deliberate step that withdraws its acceptance

### Decision: Lines already on a roadmap
- **Status:** decided
- **Decided by:** human
- **Options:** nothing written for them; backfill an `(added)` record for each on first use
- **Choice:** nothing written
- **Why:** the milestone's non-goals rule out reconstructing history, and a backfilled record would carry a date it didn't happen on

### Decision: The commands' shape
- **Status:** decided
- **Decided by:** planner
- **Options:** `wm roadmap <add|drop|move> <milestone> <change>`; flags such as `wm roadmap --milestone <m> add <change>`
- **Choice:** `wm roadmap <add|drop|move> <milestone> <change>`, with the description as a positional argument to `add`
- **Why:** the same order as `wm accept <change>` and `wm tick <change> <item>`: what it acts on, then the detail

### Decision: Records a change of plan writes
- **Status:** decided
- **Decided by:** planner
- **Options:** `(proposed)` and `(archived)` only for membership, and `(added)` only from `wm roadmap add`; also `(added)` when `wm new change --milestone` appends a new line
- **Choice:** one record per command: `wm new change --milestone` writes `(proposed)` whether it links a planned line or adds one
- **Why:** one command, one record keeps the Log easy to read, and `(proposed)` already says the change joined the plan

### Decision: Where the Log's records are parsed
- **Status:** decided
- **Decided by:** planner
- **Options:** in `record/milestones.py`, with the rest of the file; in `record/tasks.py`, which reads a change's Log
- **Choice:** `record/milestones.py`, using `records.parse`
- **Why:** the Log belongs to the milestone file, and only the record grammar is shared

## Open questions

None.

## Risks and trade-offs

- Every agent, the planner included, can no longer edit roadmap lines by hand. A skill that still says to do so is refused; the skills are updated in this change, and the refusal names the command to use.
- A roadmap line's description can't be changed through `wm`, and an agent's edit of it is refused. To reword one, a human edits the file, or the line is dropped and added again, which the Log records.
- `(archived)` is written only when the archived change's proposal names an active milestone. A change linked only by hand, from before `link-milestone-changes`, gets its roadmap line ticked but no record.
- A malformed line in a milestone's Log isn't reported as one; the reader skips lines that aren't records.

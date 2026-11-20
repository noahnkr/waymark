# Attribute log records: design

## Context

- `record/evidence/records.py` defines every record kind in `KINDS`, with its grammar, whether it has text, and its `Level` (item, change, both, or milestone). `who_for(root, by)` gives `--by`, else the git user, else None, whatever the kind. `IMPLEMENTER` and `REVIEWER` are `wm-implementer` and `wm-reviewer`.
- `services/lifecycle.py` writes the change records through `_who(record, by)`. `services/roadmap.py` has its own `_who` for the milestone records, and `services/setup.py` writes `(proposed)` when a change joins a milestone. `accept` uses the git user directly, and refuses without one.
- `tick` writes only the checkbox, takes no date or `--by`, and refuses a blocked item. `archive` writes the outcome, an `(override)` record when asked, and the milestone's `(archived)` record, then moves the folder, all in one transaction.
- `(archived)` exists only as a milestone record (`Level.MILESTONE`, grammar `CHANGE_NAME`). The task list parser reports a milestone-level record in a task list as misplaced.
- `hooks/decide.py` records an implementer's or reviewer's ending with `by=IMPLEMENTER` or `by=REVIEWER`, ticks an item from `RESULT: done`, and allows an implementer exactly one writing command, `wm note`.
- `assets.IMPLEMENTER` and `assets.REVIEWER` are the agents' file names, `wm-implementer` and `wm-reviewer`. They name the agents, not the records, and stay as they are.

## Approach

1. **Kinds.** Add `TICKED` (grammar `ITEM`, no text, item level) and `REVISED` (a new grammar, `PARTS`: an optional list of parts, no `;` needed since nothing follows it, then the text; change level). `ARCHIVED` gets a new level, `CHANGE_OR_MILESTONE`, and its grammar takes the change's name only in a milestone's Log. The parser reads a change Log's `(archived)` without a name, and the task list parser no longer reports it as misplaced.
2. **Authorship.** Replace `who_for(root, by)` with `author(root, kind, by, *, human=False)`. It returns `by` when given. Otherwise:
   - for a human kind (`ACCEPTED`, `OVERRIDE`, `RESOLVED`, `ARCHIVED`, or `TICKED` with `human=True`), the git user;
   - for every other kind, `planner for <git user>`, or `planner` without one.

   `IMPLEMENTER` and `REVIEWER` become `implementer` and `reviewer`. Every writer in `lifecycle.py`, `roadmap.py` and `setup.py` calls `author` with its kind. `accept` keeps refusing without a git user.
3. **Tick.** `tick(start, name, number, today, *, by=None)` writes `(ticked)` into the Log, in the same transaction as the checkbox. `human` is true when the item's role is `human`. The CLI gains `--by`, and the hook's `done` ending passes `by=IMPLEMENTER`.
4. **Archive.** `archive` appends `(archived) by <who>` to the change's task list, in the transaction that moves the folder, so a refused archive writes nothing.
5. **Revise.** `lifecycle.revise(start, name, why, today, *, parts=(), by=None)`, behind the new command `wm revise <change> "<why>" [--parts <part>,...] [--by <who>]`. Each part must be an item number of the change, `proposal`, `design`, or `specs/<area>` for one of its deltas. It refuses a change with no `(accepted)` record. `accept` refuses when the Log has an `(accepted)` record and no `(revised)` record after the last one, and names `wm revise`. The hook treats `revise` as a writing command, so implementers and reviewers can't run it.
6. **Implementer's note.** The hook refuses an implementer's `wm note` that doesn't carry `--by implementer`, saying to add it.
7. **Assets and docs.** `wm-update` runs `wm revise` after each confirmed edit, and when it adds an item. `wm-apply` and the implementer's definition say how records name who wrote them. `docs/record.md` and `docs/concepts.md` describe the authorship and the three new records, the CLI reference is regenerated, and the CHANGELOG says what users will see. The two stale scenarios move with the `records` delta.

## Decisions

### Decision: Who a record names
- **Status:** decided
- **Decided by:** human
- **Options:**
  - by the record's kind: the human's acts name the git user, the planner's records name `planner for <git user>`, agents name their role
  - the git user for everything run in the session, as today
  - the role alone, with no person
- **Choice:** by the record's kind
- **Why:** it names who actually wrote each record, and still says whose session it was, which a team needs.

### Decision: Agents' names in records
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `implementer` and `reviewer`, the roles a Build line and the specs use
  - `wm-implementer` and `wm-reviewer`, the agents' file names
- **Choice:** `implementer` and `reviewer`
- **Why:** the record should use the same words as the rest of the record, not a tool's file names.

### Decision: How an edit after acceptance is recorded
- **Status:** decided
- **Decided by:** human
- **Options:**
  - a `(revised)` record written by `wm revise`, which `wm accept` requires before it accepts again
  - a fingerprint per part, so a new `(accepted)` record names what changed
  - both
- **Choice:** a `(revised)` record, required before accepting again
- **Why:** it records why the change was edited, which a fingerprint can't, and the refusal at accept keeps it from being forgotten.

### Decision: Where `(archived)` lives
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - the same `(archived)` kind in both Logs, with the change's name only in a milestone's
  - a new kind for the change's own Log, such as `(closed)`
- **Choice:** the same kind in both Logs
- **Why:** it is the same event seen from two places. A second word for it would leave readers wondering how the two differ.

### Decision: How the implementer's own note is attributed
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - the hook refuses an implementer's `wm note` without `--by implementer`
  - the hook rewrites the command to add `--by implementer`
- **Choice:** refuse it, saying to add the flag
- **Why:** the hooks only allow or refuse, and never change a command. The refusal teaches the agent the flag the first time.

### Decision: Existing records
- **Status:** decided
- **Decided by:** human
- **Options:**
  - leave them as written
  - rewrite them under the new rule
- **Choice:** leave them
- **Why:** who wrote an old record can't be known from the record, so a rewrite would guess.

## Open questions

None.

## Risks and trade-offs

- `wm` decides who a record names from its kind, not from who typed the command. A note the human typed reads `by planner for Ada` unless they pass `--by`.
- `wm revise` can't check that its text says truly what changed. The refusal at accept only makes sure something was written.
- When a spec the change modifies moves on, acceptance is withdrawn without an edit to the change, and accepting again still needs a `(revised)` record. That record then says what was rebased, which is worth recording anyway.
- The Log grows by one line per item, for the ticks.

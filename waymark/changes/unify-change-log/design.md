# Unify change log: design

## Context

This design assumes `restyle-record` is built: records are written `<date> (<kind>) [<args>] [by <who>]: <text>`, labels are bold, and every item has a Build line.

- **Reading.** `record/artifacts/tasks.py` reads a task list in one pass. `item_record` reads a record under an item into the item's draft, refusing change-level and milestone kinds as `misplaced-record`. `log_record` reads a Log record into `Tasks.log`, refusing item kinds as `misplaced-record` ("goes under that item"). `Item.records`, `Item.notes`, and the `blocked` and `spec_gap` worked out by `_open_stoppers`, come from the records under the item.
- **Who reads item records.** `record/state.py` counts `(reopened)` records in `item.records`; `services/context.py` takes an item's `(resolved)` texts and notes for the implement pack; `views/payloads.py` writes `item.records` into `wm show --json`; `services/lifecycle.py` reads `item.blocked` and `item.spec_gap`. None of them reads the file directly.
- **Writing.** `services/lifecycle.py` writes `(blocked)` and `(gap)` (`_add_stopper`), `(note)`, `(reopened)` (`reopen`) and `(resolved)` (`resolve`) under the item, and the change-level records at the end of the Log. Agent endings go through the same functions.
- **Records.** `record/evidence/records.py` gives each kind a `Level` (`ITEM`, `CHANGE`, `BOTH` for `(resolved)`, `MILESTONE`) and a `Grammar`; the item kinds carry no argument today.
- **Hooks.** `record/evidence/evidence.py` treats any record line in a task list as evidence, wherever it is, so an agent can't add one by hand.
- **Archive.** Archived changes hold their item records under their items, in the restyled shape once `restyle-record` has rewritten them.

## Approach

1. **The item argument.** In `records.py`, the item kinds `(blocked)`, `(gap)`, `(note)` and `(reopened)` get a new `Grammar.ITEM`: one item number, required. `(resolved)` takes an optional item number: with one it resolves that item, without one the review. `Level.ITEM` and `Level.BOTH` now mean "in the Log, naming an item", and a record that names an item the change doesn't have is reported as `unknown-item`.
2. **Reading from the Log, in two steps.** `log_record` accepts item records and keeps every record in `Tasks.log`, in file order. After the pass, each item's records are gathered from the Log by the item they name, so `Item.records`, `notes`, `blocked` and `spec_gap` are built as before and nothing downstream changes. `_open_stoppers` runs over one item's records, so a `(resolved)` for 1.2 doesn't clear 1.1. Change-level queries (`Tasks.latest`, `review_records`) skip records that name an item. In the first step, records under an item are still read into the item; once the archive is rewritten, `item_record` reports any record under an item as `misplaced-record`, saying it belongs in the Log.
3. **Writing to the Log.** `_add_stopper`, `note`, `reopen` and `resolve` append to the Log through the same function that writes change-level records, creating the section when needed, with the item number as the argument.
4. **Views.** `wm show` keeps an item's `records` in its JSON and shows them under the item in text, and adds the Log as written; the implement pack keeps its notes and resolutions per item. A JSON schema whose fields change has its version raised.
5. **Hooks.** No change to evidence detection, beyond the messages: refusing a record added by hand under an item or in the Log names the `wm` command.
6. **The archive.** A Python script run from the scratchpad, never committed, moves each archived item record into its change's Log, adding the item number after the kind. A record goes after the last Log record whose date is on or before its own, and after the item records of the same day placed before it, in item order; it creates a Log section where an archived change has none. It changes nothing else.
7. **Skills and docs.** `wm-apply`, `wm-implementer` and the docs say an item's records are in the Log, naming the item.

## Decisions

### Decision: Where a record names its item
- Status: decided
- Decided by: human
- Options:
  - an argument straight after the kind, `2026-11-20 (note) 1.2 by Ada: …`
  - inside the kind, `2026-11-20 (note 1.2) by Ada: …`
- Choice: an argument after the kind
- Why: it is the existing record shape, the way a milestone record names its change; a second shape would need its own reading and checks.

### Decision: Order of archived item records
- Status: decided
- Decided by: human
- Options:
  - by date, after the Log records of the same day
  - placed by a rule, such as a `(reopened)` right after the review that named its item
  - left under their items in the archive
- Choice: by date, after the day's Log records
- Why: it is simple and predictable, and affects only the archive; rules that run once aren't worth their risk, and leaving them would keep a second placement in the reader for good.

### Decision: What the views show
- Status: decided
- Decided by: human
- Options:
  - each item's records with the item, gathered from the Log, and the Log as written
  - the Log only
- Choice: gathered with the item, and the Log as written
- Why: an implementer and a reader of `wm show` still see an item's blockers and notes beside it, while the file holds one history.

### Decision: How item records reach the code that reads them
- Status: decided
- Decided by: planner
- Options:
  - gather them from the Log into `Item.records` after parsing, so readers are unchanged
  - give `Tasks` a lookup by item and change every reader to use it
- Choice: gather into `Item.records`
- Why: the state, context, views and commands keep working on items as they do, and the change stays in the parser and the writers.

### Decision: How the reader moves to the Log
- Status: decided
- Decided by: planner
- Options:
  - read both places first, rewrite the archive, then report records under items
  - switch reader, writers and files in one item
- Choice: both places first
- Why: `wm` on PATH runs this checkout, and this change's own items may get records while it is built; reading both keeps `wm check` healthy after every item.

## Open questions

None.

## Risks and trade-offs

- **The overlap with `restyle-record`.** Both change "Item records", "Log section" and "Ending recorded from a final message". These deltas are written against the text `restyle-record` leaves; once it is archived, this branch is rebased onto the default branch, its files are brought to the new layout, and it is accepted again.
- **A change-level query that counts an item record.** `Tasks.latest` and the review records must skip records naming an item, or a `(resolved)` for an item would read as resolving the review. A test covers each.
- **Same-day order in the archive** is approximate, as decided; the dates stay true.
- **Given up:** reading item records under items.

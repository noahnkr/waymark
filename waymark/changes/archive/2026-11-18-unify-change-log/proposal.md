# Unify change log

- **Owner:** Noah Roberts
- **Review:** independent

## Why

A change's history is split across its task list. What happens to the change as a whole (acceptances, reviews, overrides) is in the `## Log`, while what happens to one item (a block, a spec gap, a note, a reopen, a resolution) sits under that item. A review that asks for changes is in the Log, but the `(reopened)` records it causes are scattered under three items, and the acceptance that follows is back in the Log. Reading what happened, and in what order, means reading the whole file and putting it together by date, which loses the order within a day.

Once `restyle-record` puts the date first on every record, the Log reads as a timeline; holding every record there makes it the change's one history.

## What changes

- **Every record of a change goes in its `## Log`**, in the order it was written. A record about one item names the item as its argument, straight after the kind: `2026-11-20 (blocked) 1.2 by Ada: the API key is missing`, and the same for `(gap)`, `(note)`, `(reopened)` and `(resolved)` with an item.
- **An item holds only its definition and its tick.** `wm check` reports a record under an item in an active change, saying it belongs in the Log.
- **The views still show an item's records with it.** `wm show` and the implement pack gather each item's records from the Log, so an item's blockers, notes and resolutions still appear beside it.
- An item is blocked, reopened or resolved as before; only where the record is written changes.
- This record moves to the new placement: this change's own records by hand, and the archived changes once, by a script that is run and not committed. Archived item records go into their Log by date, after the change records of the same day. The record stays at format 1.

## Non-goals

- Changing a record's shape beyond the item argument: `restyle-record` does that.
- Moving a milestone's Log; it already holds every milestone record.
- Exact order within one day in the archive: records carry a date, not a time, so the rewrite places an item record after the change records of its day.
- Reading item records under items: `wm` reads only the new placement, and no command migrates a record.

## Impact

- **Specs:** `acceptance`, `agent-results`, `records` (modified)
- **User-visible:**
  - `wm block`, `wm gap`, `wm note`, `wm reopen`, `wm resolve <change> <item>` and an implementer's ending write their record into the change's `## Log`, naming the item, not under the item
  - `wm check` reports a record under an item in an active change
  - `wm show` and the implement pack still show each item's records with the item
- **Code:** `record/` (`evidence/records.py`, `artifacts/tasks.py`, `evidence/evidence.py`), `services/` (lifecycle, check, agent results), `hooks/decide.py`, `views/` only if a payload's shape changes, the skills and agent definitions in `assets/`, the tests, the docs and the CHANGELOG, and this record's archived changes

## Outcome

- **Built:** Every record of a change now goes in its Log: wm block, wm gap, wm note, wm reopen, wm resolve <change> <item> and an implementer's ending name the item after the kind, wm show and the implement pack gather each item's records from the Log, and wm check reports a record under an item as misplaced-record. The archive's item records were moved into their Logs by an uncommitted script.
- **Differs:** The delta was revised during the build so that only wm show, not the review pack, shows the Log as written; the review pack still leaves notes out. Left open from the review: in keep-agent-setup-local, items 1.1 and 2.1 list their records in date order, which differs from the order they were written in (warning); the Implementer partly done test doesn't check that the note ends the Log (suggestion).

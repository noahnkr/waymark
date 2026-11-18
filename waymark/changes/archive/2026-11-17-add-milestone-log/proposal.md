# Add milestone log

- Owner: Noah Roberts
- Milestone: stronger-milestones
- Review: independent

## Why

A milestone's roadmap is the plan for the work still being discovered, and it changes as that work goes: lines are added, dropped and reordered. Today anyone edits the roadmap by hand, nothing records why a line went or when the plan changed, and a line for a change that was never proposed doesn't stop `wm close`, so a milestone can close with planned work quietly left behind. The roadmap should show the plan as it stands, change only through `wm`, and keep a history of how it got there.

This is the second change of `stronger-milestones`. It builds on `link-milestone-changes`, which made each change name its milestone.

## What changes

- **`wm roadmap` changes the roadmap.** `wm roadmap add <milestone> <change> "<description>"` adds a planned line at the end. `wm roadmap drop <milestone> <change> --reason "<why>"` removes a line; it refuses a line whose change is active and names the milestone, which must leave the milestone first. `wm roadmap move <milestone> <change> --after <other>` or `--first` reorders it.
- **A milestone keeps a `## Log`.** It is the last section of `milestone.md`, written only by `wm`, and holds a dated record for each change to the plan: `(added)`, `(dropped)` with its reason, and `(moved)` from `wm roadmap`; `(proposed)` from `wm new change --milestone`; `(archived)` from `wm archive`. The Log starts with the first record after this change; lines already on a roadmap aren't backfilled.
- **Roadmap lines are evidence.** An agent's edit that adds, changes or removes a roadmap line or a record in a milestone's Log is refused and pointed at `wm roadmap`, as an edit to a task list's ticks and records is today. A human's own edits aren't stopped.
- **`wm close` needs every line archived.** A planned line that was never proposed now keeps the milestone open; it is dropped with a reason first, so the Log says why.
- **Skills** that wrote roadmap lines by hand use `wm roadmap`.

## Non-goals

- Change dependencies, branches and bases: that is `add-change-dependencies`.
- Replaying the Log to check a roadmap against it, or reconstructing a roadmap's history from git.
- Stopping a human's own edits to `milestone.md`.
- Editing a roadmap line's description through `wm`.
- Reviewing a milestone as a whole.

## Impact

- Specs: `milestones` (the Log section in the milestone file, `wm roadmap`, the milestone Log and its records, roadmap lines as evidence, closing a milestone, and the proposed record from `wm new change --milestone`).
- User-visible:
  - new commands `wm roadmap add`, `wm roadmap drop --reason` and `wm roadmap move --after|--first`;
  - a `## Log` section at the end of `milestone.md`, written by `wm new change --milestone`, `wm archive` and `wm roadmap`;
  - agents' edits to roadmap lines or a milestone's Log are refused;
  - behavior change: `wm close` refuses a milestone with a planned line that was never proposed, until it is dropped.
- Code: the record kinds and their grammar (`record/records.py`), the milestone file and its Log (`record/milestones.py`, `record/evidence.py`), the roadmap commands (`cli.py`, a new service), `wm new change` (`services/setup.py`), `wm archive` and `wm close` (`services/lifecycle.py`), the hooks (`hooks/decide.py`), the `wm-explore`, `wm-propose` and `wm-archive` skills, and the docs.

## Outcome

- Built: A milestone roadmap now changes only through wm roadmap add, drop --reason and move --after|--first, each writing a record in a ## Log at the end of milestone.md, as do wm new change --milestone and wm archive. The hooks refuse an agent hand edit to a roadmap line or the Log. wm close needs every roadmap line archived. The wm-explore and wm-archive skills and the docs use wm roadmap.
- Differs: The independent review passed with four findings left open: a planned line that does not start with a change name blocks wm close and cannot be dropped through wm, so only a human edit unblocks it; move writes a (moved) record even when the line does not change place; item 1.3 close tests are in test_milestones.py, not the test_lifecycle.py its Verify line names, as noted on the item; and wm new change --milestone has no --by for its (proposed) record. Also, a milestone record found in a change task list is reported as misplaced, which the design did not mention.

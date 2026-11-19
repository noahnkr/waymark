# Add exploration lifecycle

- **Owner:** Noah Roberts
- **Review:** independent

## Why

An exploration is how the project keeps research and backlogs ideas, but nothing in `wm` ends one. When an exploration leads to a change, the planner writes `led-to` on its Status line by hand, and the exploration stays in the active list long after its work is archived: `lighter-workflow` still shows in every explore context pack, though its milestone closed on 2026-11-15. An idea that was weighed and rejected has nowhere to go but `parked`, which reads the same as an idea still waiting. And picking a saved exploration back up has no defined steps, so a session may start from a blank page instead of from what was already written.

The backlog should hold only live ideas, every way an exploration ends should be written by the `wm` command that causes it, and resuming one should follow the same steps every time.

## What changes

- **Three statuses.** An exploration is `open` (waiting to be decided or built), `led-to <links>` (its findings went into a change or milestone) or `dropped` (it was weighed and won't be acted on). `parked` is removed; an open exploration may say in its Conclusion what it waits for.
- **`--from` writes `led-to`.** `wm new change <name> --from <exploration>` and `wm new milestone <name> --from <exploration>` set the exploration's Status line to `led-to` with a link to the new change or milestone. Naming an exploration that already led somewhere adds the new link to the line.
- **Archived when its work is.** `wm archive <change>` and `wm close <milestone>` move each exploration whose `led-to` targets are then all archived or closed to `explorations/archive/<date>-<name>.md`, in the same operation.
- **`wm exploration drop`.** `wm exploration drop <exploration> --reason "<why>"` sets the status to `dropped`, writes the reason into the Conclusion and moves the exploration to the archive, in one step.
- **Status lines are evidence.** An agent's hand edit to an exploration's `- Status:` line is refused and pointed at `--from` and `wm exploration drop`. `wm new exploration` still writes `open`.
- **Archived explorations stay readable.** `wm show <exploration>` finds an archived one, and `wm ls explorations --archived` lists them. The explore context pack lists active explorations only.
- **`wm check`** reports a `led-to` exploration whose targets are all archived or closed but which is still active, and a `parked` status as unknown.
- **Resuming an exploration.** `/wm-explore <exploration>` reads the saved exploration, says what has changed in the record since it was written, continues from its Questions and Approaches, and closes with the four offers for a resumed exploration: leave it open, update it or drop it, turn it into a proposal, or turn it into a milestone, the last two with `--from`.
- **An `explorations` spec** holds this behavior; the Exploration status requirement moves there from `authored-formats`.
- This repository's `lighter-workflow` exploration moves to the archive.

## Non-goals

- Migrating `parked` explorations: the record format stays 1, and no record in use holds one.
- Stopping a human's own edits to an exploration's Status line.
- Reopening an archived exploration, or undoing a drop.
- Archiving an exploration when its change is abandoned: an abandoned change's branch is deleted, and the `led-to` link goes with it.
- Telling from git when an exploration was last written; the resume step compares it with the record as it stands.

## Impact

- **Specs:**
  - `explorations` (added: statuses, the from option, archiving with the work, dropping, status lines as evidence, archived explorations in show and ls, the stale led-to check);
  - `authored-formats` (Exploration status removed, moved to the new spec);
  - `skills` (Explore's closing offers modified for a resumed exploration; resuming an exploration added);
  - `setup` (Record folders kept in git modified: the explorations archive folder gets a gitkeep).
- **User-visible:**
  - new command `wm exploration drop <exploration> --reason "<why>"`;
  - new `--from <exploration>` option on `wm new change` and `wm new milestone`;
  - `wm archive` and `wm close` move explorations to `explorations/archive/<date>-<name>.md`;
  - record format: `parked` is no longer a status, and `dropped` is new; the `wm.show.exploration` and `wm.context.explore` JSON list `dropped` instead of `parked`;
  - `wm init` and `wm update` write `explorations/archive/.gitkeep`;
  - `wm show` finds archived explorations, and `wm ls explorations --archived` lists them;
  - agents' edits to an exploration's Status line are refused;
  - `wm check` reports a `led-to` exploration left active after its work is archived;
  - `/wm-explore <exploration>` resumes a saved exploration.
- **Code:** the exploration artifact and state (`record/artifacts/explorations.py`, `record/state.py`, `record/record.py`), the exploration template, `wm new` (`services/setup.py`, `cli.py`), `wm archive` and `wm close` (`services/lifecycle.py`), a new drop service and command, `wm check` (`services/check.py`), the views (`views/payloads.py`, `views/render.py`, `views/schemas.py`), the hooks (`hooks/decide.py`, `record/evidence/evidence.py`), the `wm-explore` and `wm-propose` skills, the docs and the CHANGELOG, and this record's `lighter-workflow` exploration.

## Outcome

- **Built:** An exploration is open, led-to or dropped, and only wm writes its status line: wm new change --from and wm new milestone --from write led-to, and wm exploration drop --reason writes dropped with the reason and archives it. wm archive and wm close move an exploration to explorations/archive/<date>-<name>.md once all its work is archived, re-aiming links to it; wm show and wm ls --archived read archived ones; wm check reports exploration-not-archived; the hooks refuse an agent's hand edit to the status line; /wm-explore <exploration> resumes a saved one with four offers. lighter-workflow is archived.
- **Differs:** Beyond the design, the move also re-aims links to the exploration from the rest of the active record, including the change or milestone archived with it (the first independent review found these dangling), and wm exploration drop refuses an exploration with no Conclusion. The show.exploration JSON field is archived_on, matching wm.show.change; item 1.2's criterion was revised to say so, and the change was accepted again. Item 1.3's commit scope was services, since check isn't a project scope.

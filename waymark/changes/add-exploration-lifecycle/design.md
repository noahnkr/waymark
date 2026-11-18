# Add exploration lifecycle: design

## Context

- **Parsing.** `record/artifacts/explorations.py` reads an exploration's `- Status:` line with `_STATUS` (`open|parked|led-to`), and for `parked` requires a Conclusion (`parked-without-reason`). `record/state.py` turns it into an `ExplorationState`, with `ExplorationStatus` `OPEN`, `PARKED`, `LED_TO` and `UNREADABLE`; `_state_from_status` resolves `led-to` links with `_member`, which already reads active and archived change and milestone folders.
- **Loading.** `record/record.py` loads `explorations/*.md` with `_load_markdown_folder`, which reports any folder inside it as `unexpected-file`. Changes and milestones split active from archived with `_split_folder`, and keep the archived ones as `ArchiveEntry` tuples (`archived_changes`, `archived_milestones`). `Record.documents()` yields active explorations, so `wm archive` and `wm close` already re-aim links in them.
- **Archive and close.** `services/lifecycle.py` `archive()` and `close_milestone()` each build one `Transaction`: they rewrite links in `record.documents()` with `record/writing/moves.py` `rewrite_links`, then `transaction.move(source, target)`. `ArchiveName(date, name).folder` and `parse_archive_name` give and read `YYYY-MM-DD-<name>`.
- **Creating.** `services/setup.py` `create_change()` and `create_milestone()` write from templates in their own transactions; `cli.py` wires `wm new` with `--milestone` and `--after`.
- **Hooks.** `hooks/decide.py` `_edit()` refuses an agent edit that changes evidence, found by `record/evidence/evidence.py` `evidence(relative, text)`, which today covers task lists and active milestones and names the commands to use instead (`_ROADMAP_COMMANDS`, `_EVIDENCE_COMMANDS`).
- **Views.** `views/payloads.py` builds `wm show`, `wm ls` and the explore context (through `services/context.py`); `views/schemas.py` holds the JSON schemas, whose versions are in `payloads.py`. `docs/json.md` says a removed or changed field raises a schema's version.
- **Setup.** `services/setup.py` writes the `.gitkeep` files for the record's folders.

## Approach

1. **Statuses.** In `explorations.py`, `_STATUS` reads `open|led-to|dropped`; `parked`, `PARKED` and the `parked-without-reason` problem go. The unknown-status and missing-status messages list the three statuses. `ExplorationStatus` gets `DROPPED` in place of `PARKED`. The template's comments describe the three statuses and say an open exploration may note in its Conclusion what it waits for.
2. **Archived explorations in the record.** `_load_markdown_folder` skips the `archive` folder inside `explorations/`, and a new loader reads `explorations/archive/*.md` into `Record.archived_explorations: tuple[ArchiveEntry, ...]` with `parse_archive_name` on the file's stem; a file that doesn't parse is reported as `invalid-name`, as for changes. Archived explorations are not in `Record.documents()`, so they aren't checked or fixed, the same as archived changes.
3. **Status line writer.** A function in `explorations.py`, `with_led_to(exploration, link) -> str`, returns the document's text with the Status line set to `led-to <link>`, or with `, <link>` added when it is already `led-to`, editing only that line. `with_dropped(exploration, reason) -> str` sets `dropped` and adds the reason as the Conclusion's last paragraph.
4. **`--from`.** `wm new change` and `wm new milestone` take `--from <exploration>`. `create_change` and `create_milestone` look the exploration up among the active ones (refusing an unknown one before writing anything) and stage `with_led_to` with a link relative to `explorations/`, in the same transaction that writes the change or milestone.
5. **One move helper.** `services/lifecycle.py` gains `_archive_explorations(record, transaction, staged_texts, today)`. Run after the link rewrites in `archive()` and `close_milestone()`, it reads each active exploration's staged text, and when every `led-to` target now resolves to an archived change or milestone (counting the one being moved), it re-aims the exploration's own links from `explorations/archive/` with `rewrite_links` and moves the file to `explorations/archive/<date>-<name>.md`. A target already taken that day refuses the whole operation, before anything is written.
6. **`wm exploration drop`.** A new `exploration` command group in `cli.py` with one subcommand, `drop <exploration> --reason "<why>"`, calling a new `services/lifecycle.py` `drop_exploration()`. It refuses an unknown exploration (naming the active ones) and a `led-to` one, writes `with_dropped`, re-aims its links and moves it, in one transaction.
7. **Check.** `services/check.py` reports an active exploration whose `led-to` targets all resolve to archived ones as an error, `exploration-not-archived`, naming `explorations/archive/`. `state.py` reads that state as `LED_TO` as before; the check reads the resolved targets.
8. **Hooks.** `evidence()` gains a third case: for `explorations/<name>.md` (not the archive), the Status line is evidence, named `the "- Status:" line`. `_edit()` names `_EXPLORATION_COMMANDS` ("wm new change --from <exploration>, wm new milestone --from <exploration> or wm exploration drop <exploration> --reason "<why>"") for an exploration path.
9. **Views.** `wm show` looks in the archived explorations after the active ones, by name or dated name, and the payload adds `archived` (a date or null). `wm ls explorations --archived` adds the archived ones with an `archived` state. The status enum in `wm.show.exploration` and `wm.context.explore` becomes `open`, `led-to`, `dropped`. Text views print "Archived on <date>".
10. **Setup.** `explorations/archive/` joins the folders that get a `.gitkeep`.
11. **Skills.** `wm-explore` gains a first step for resuming (read with `wm show`, report what changed in the record, continue from Questions and Approaches) and closing offers for a resumed exploration; offer 3 and 4 pass `--from`, and the hand-written `led-to` instruction goes. `wm-propose`'s naming step passes `--from <exploration>` when the work comes from one.
12. **Docs.** `docs/concepts.md` (glossary, lifecycle, record layout), `docs/cli.md` and `docs/json.md` regenerated by `tools.docs`, and a CHANGELOG entry.
13. **This record.** `lighter-workflow` moves to `explorations/archive/2026-11-15-lighter-workflow.md` with `git mv`, dated the day its milestone closed, and its relative links are re-aimed by hand.

## Decisions

### Decision: When a led-to exploration is archived
- Status: decided
- Decided by: human
- Options: when its targets are archived or closed (with the work); when the work starts, at `--from` (at hand-off); by hand, with a check that warns
- Choice: with the work
- Why: the move lands in the same operation, and the same pull request, as the archive that ends it, so no link dangles and nothing is left to tidy. At hand-off an archived file would link to an active change, and the archive would have to re-aim links in archived explorations too.

### Decision: Parked replaced by dropped
- Status: decided
- Decided by: human
- Options: keep parked beside a new dropped status; replace parked with dropped
- Choice: replace
- Why: parked and open both mean waiting; dropped is a different thing, an active decision not to act, and only `wm exploration drop` writes it.

### Decision: No migration for parked
- Status: decided
- Decided by: human
- Options: raise the record format and migrate; read parked as open; drop parked outright at format 1
- Choice: drop it outright at format 1
- Why: this repository is the only record in use, and it holds no parked exploration.

### Decision: The drop command
- Status: decided
- Decided by: human
- Options: `wm drop <exploration> --reason`; `wm exploration drop <exploration> --reason`
- Choice: `wm exploration drop`
- Why: a command group for explorations leaves room for more subcommands, and reads unambiguously beside `wm roadmap drop`.

### Decision: Guarding the Status line
- Status: decided
- Decided by: human
- Options: refuse agents' hand edits in the hooks; leave it to `wm check`
- Choice: the hooks refuse them
- Why: `led-to` and `dropped` are written only by `wm`; the hooks already guard roadmap lines the same way.

### Decision: More than one led-to target
- Status: decided
- Decided by: human
- Options: append the new link; refuse an exploration that already led somewhere
- Choice: append
- Why: one exploration can split into several changes, and it is archived once all of them are.

### Decision: An exploration already left behind
- Status: decided
- Decided by: human
- Options: `wm check` reports it and this change moves `lighter-workflow` once; `wm check --fix` moves such explorations
- Choice: report it, and move `lighter-workflow` once
- Why: `--fix` promises layout only, never moves; once the archive exists the state can only come from a hand edit.

### Decision: Archived exploration as a file
- Status: decided
- Decided by: planner
- Options: one file `explorations/archive/<date>-<name>.md`; a folder `explorations/archive/<date>-<name>/exploration.md`
- Choice: one file
- Why: an exploration is one file today, its links stay one level deep, and `parse_archive_name` reads the stem as it reads a folder name.

### Decision: Same-day name clash in the archive
- Status: decided
- Decided by: planner
- Options: refuse the whole operation; add a suffix to the file name
- Choice: refuse
- Why: it matches `wm close` for a milestone closed twice in a day, keeps archived names parseable, and needs a reused exploration name, which is rare.

### Decision: JSON schema versions
- Status: decided
- Decided by: planner
- Options: raise `wm.show.exploration` and `wm.context.explore`; keep them at their versions
- Choice: raise them; `wm.ls` keeps its version, since it only gains entries
- Why: `docs/json.md` says a changed field raises the version, and the status enum loses `parked`.

## Open questions

None.

## Risks and trade-offs

- **An agent can't write a new exploration by hand.** Writing a whole file adds a Status line, which the hook refuses; the agent uses `wm new exploration`, as the skills already say.
- **`wm archive` can now be refused by an exploration**, when an exploration of the same name was archived that day. The refusal names the clash; renaming the exploration settles it.
- **Archived explorations aren't checked.** A broken link in one, from a target renamed later, goes unreported, as in archived changes.
- **An abandoned change leaves `led-to` pointing nowhere** on its branch only; on the default branch the change and the link never land. A change abandoned after merge doesn't exist in this workflow.

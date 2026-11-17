# Reset record format

- Owner: Noah Roberts
- Review: independent

## Why

The record is at format 3, and the number tells only of formats 1 and 2, which no record is in any more: this repository's record is the only one there is, and it is at format 3. The code still carries what those formats left behind. The migration machinery runs no migration, since none is left. Checks report lines of older layouts and tell the user to run `wm update` to migrate them, which `wm update` can't do. `wm` still reads 0.1.1's atlas pointer, and `wm doctor` still looks for the git hooks 0.1.0 committed. All of it is code to maintain and messages that point nowhere.

## What changes

- The record format becomes 1, and this `wm` reads and writes only format 1. This repository's record moves from 3 to 1.
- A record in any other format, older or newer, gets one reason everywhere: it names the record's format, says this `wm` reads only format 1, and says to install the `wm` version that wrote it. `wm update`, `wm init` in a clone and the writing commands refuse it; `wm check` and `wm doctor` report it.
- No migration code is left: `wm update` regenerates the files `wm` owns and adds missing `.gitkeep` files, and migrates nothing.
- The readers of older layouts go. `wm check` no longer reports a line as an older layout or an older record format; such a line is held to the current layout like any other, and fails the check that applies to it. The old milestone files `goal.md` and `roadmap.md` are no longer named on their own.
- `.waymark/atlas.toml` is no longer read as an atlas pointer, `wm atlas point` no longer removes it, and `wm doctor` no longer looks for `.waymark/hooks/`.
- The tests named after format 2 are renamed after what they test.

## Non-goals

- No guard for a record made by 0.1.x, which is also format 1 but laid out differently: no such record exists, so it would be read as format 1 and fail the checks rather than be refused.
- Archived changes are not rewritten; they are read as they were written, as before.
- The `wm` version is not bumped here; the release does that.
- The CHANGELOG's released entries are not edited.

## Impact

- Specs: `authored-formats` (modified, renamed), `formatting` (modified), `setup` (modified), `atlas` (removed)
- User-visible:
  - new records are written at `record_format = 1`; a record at format 3, from wm 0.2.0, is refused with the reason to install the `wm` version that wrote it
  - one reason for a record in another format, from every command, with no mention of `wm update`
  - `wm check` no longer has the problem codes `old-layout` and `old-record-format`; lines in an older layout fail the current checks
  - `wm update`'s help no longer says it migrates the record
  - `.waymark/atlas.toml` is no longer read, and `wm doctor` no longer reports `.waymark/hooks/`
- Code: `record/config.py`, `record/edits.py`, `record/outline.py`, `record/proposal.py`, `record/charter.py`, `record/deltas.py`, `record/tasks.py`, `record/changes.py`, `record/milestones.py`, `record/record.py`, `record/pointer.py`, `record/project.py`, `record/atlas.py`, `services/migrations.py` (removed), `services/integration.py`, `services/common.py`, `services/check.py`, `services/doctor.py`, `services/setup.py`, `services/atlas.py`, `cli.py`, the tests, this repository's `waymark/config.toml`, and the docs (`record.md`, `getting-started.md`, `multi-repo.md`, `cli.md` generated, the CHANGELOG's preamble)

## Outcome

- Built: The record format is 1, and wm reads and writes only format 1. Every command gives one reason for a record in any other format: install the wm version that wrote it. The migration code, the readers of older layouts, 0.1.1's .waymark/atlas.toml pointer and 0.1.0's .waymark/hooks check are gone, and this repository's record moved from 3 to 1.
- Differs: The glossary's old-form line is reported as glossary-format instead of the new layout code, a revision decided during the build that withdrew and renewed acceptance. Only proposal facts require the bullet; a spec's Repos line stays a bare fact. The first independent review found the settings template still said wm update advances the format; item 1.1 was rebuilt and the second review passed. getting-started.md's two 0.1.x upgrade paragraphs were replaced, beyond item 2.1's criteria. Left open: the release skill still says to state what wm update migrates (tools/skills/waymark-release/SKILL.md:33), and a task item's delegate always starts as False (tasks.py:292).

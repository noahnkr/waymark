# Keep empty record folders

- Owner: Noah Roberts
- Path: short

## Why

`wm init` writes only `waymark/config.toml` and `waymark/charter.md`. The folders the record is made of, such as `specs/`, `changes/` and `explorations/`, appear only once something is written into them. Git doesn't track empty folders, so a freshly committed record doesn't show its layout, and a folder vanishes from a clone when its last file moves out, as `changes/` does when the last active change is archived.

## What changes

- `wm init`, when it creates a record, writes an empty `.gitkeep` into each of the six record folders: `specs/`, `changes/`, `changes/archive/`, `explorations/`, `milestones/` and `milestones/archive/`.
- `wm update` writes the `.gitkeep` that is missing from any of those folders in an existing record, lists each as created, and asks the user to review and commit the record.
- A `.gitkeep` stays once written: no `wm` command removes it, also after its folder fills up and after it empties again.

## Non-goals

- No change to `wm init` in a clone that already has a record: it still sets up the machine and changes nothing under `waymark/`.
- `wm check` and `wm doctor` don't report a missing `.gitkeep`; `wm update` is what adds it.
- No `.gitkeep` inside a change, milestone or archived folder, and none in a code repo that points at an atlas.
- No new record format; the reader already skips hidden files, so no migration is needed.

## Impact

- Specs: `setup` (added)
- User-visible:
  - `wm init` creates the six record folders, each with an empty `.gitkeep`, so a new record is committed with its whole layout
  - `wm update` adds any missing `.gitkeep`, lists it as `created:`, and asks to review and commit `waymark/`
- Code: `services/setup.py` and `services/integration.py`, the setup, integration and archive tests, and the docs (`record.md`, `smoke-test.md`)

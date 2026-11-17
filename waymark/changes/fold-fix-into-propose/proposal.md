# Fold fix into propose

- Owner: Noah Roberts
- Review: independent

## Why

The size of a piece of work is often unknown until someone has looked at the specs and the code. Today the human has to pick a skill by size before that: `wm-fix` for tiny work, `wm-propose` for a change. `wm-propose` then asks the human which path to take, although `wm-explore` is where that conversation belongs. Work that starts tiny and turns out to change a requirement hands over from one skill to another.

Removing a skill brings up a second gap: `wm init` and `wm update` write the skills `wm` ships but never remove one it stopped shipping, so a machine set up earlier keeps a stale `/wm-fix`.

## What changes

- `wm-propose` is the one skill that does work, at the size the work turns out to need. It reads the specs and the code, picks the path itself and says why:
  - **tiny:** it shows one line, what it will change and the requirement it keeps to, and builds only after the human's yes; then it checks, commits and offers a pull request, as `wm-fix` did;
  - **short:** a change with no design, only when nothing is left to settle;
  - **full:** a change with a design; any question the record and the exploration didn't settle goes under the design's `## Open questions`, which blocks acceptance until the human answers.

  It no longer asks the human which path to take, and it switches from tiny to a change in the same session when the work turns out to change a requirement.
- `wm-fix` is no longer shipped. `wm-explore` offers four ways on: do nothing, save an exploration, start a proposal (any size) or start a milestone. `wm-onboard` and `wm-update` stop naming `wm-fix`.
- `wm init` and `wm update` remove every `wm-*` skill folder that `wm` no longer ships, from the shared skills folder and each agent tool's skills folder, and say which they removed.

## Non-goals

- No change to the tiny path's rules in `paths`: tiny work still needs the human's yes in the session, and still leaves nothing in the record.
- No `wm drop` command for a change that turns out tiny; `wm-propose` decides before it creates the change.
- Agent definitions (`wm-implementer`, `wm-reviewer`) aren't pruned; none has been retired.
- No change to `wm-archive` or `wm sync`.

## Impact

- Specs: `skills` (added), `setup` (added)
- User-visible:
  - the `wm-fix` skill is gone; tiny work starts from `wm-explore` or `wm-propose`
  - `wm-propose` picks the path itself and asks only for a yes before tiny work, or for answers through the design's open questions
  - `wm-explore`'s closing offers drop "Fix it on the tiny path"
  - `wm init` and `wm update` remove retired `wm-*` skill folders and list them as removed
- Code: the skills in `src/waymark/assets/` and their list, `services/integration.py`, the adapter base and the Claude Code adapter, `record/store.py`, the tests, and the docs (`concepts`, `getting-started`, `skills`, `smoke-test`, README)

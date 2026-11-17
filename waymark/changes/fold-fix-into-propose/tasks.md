# Tasks

## 1. Skills

- [x] 1.1 Make `wm-propose` choose the path and carry the tiny path
  - Criteria:
    - step 1 is "Investigate and choose the path": read the specs and the code, choose tiny, short or full by the rules of "Propose picks the path", say why, and ask the human nothing about the path
    - a `## The tiny path` section, between Steps and Quality bar, holds `wm-fix`'s steps: the one-line confirmation and the wait for a yes, then branch, build, check, commit and offer a pull request that says why no requirement changes; if a requirement turns out to change, stop building and draft a change
    - an open question left after step 2 puts the change on the full path, under the design's `## Open questions`; short is chosen only with none left
    - the rules say "Write code only on the tiny path" and "Don't merge"; nothing names `wm-fix`
  - Verify:
    - tests in `tests/test_skills.py` for the scenarios "Path chosen by the planner" and "Open questions"
    - `tests/test_skills.py` layout tests
- [x] 1.2 Retire `wm-fix` and update the skills that named it
  - Criteria:
    - `src/waymark/assets/skills/wm-fix/` is deleted and `wm-fix` is out of `assets.SKILLS`
    - `wm-explore` closes with four offers: do nothing, save an exploration, start a proposal (any size, with `wm-propose`), start a milestone
    - `wm-onboard` and `wm-update` name `wm-propose` where they named `wm-fix`, and no shipped skill or agent names `wm-fix`
    - the "section out of place" test uses another skill; the agent snapshots are regenerated if they change
  - Verify:
    - tests for the scenarios "New project" and "No tiny-path offer"
    - the assets and adapter tests

## 2. Pruning

- [x] 2.1 Remove retired `wm-*` skill folders in `wm init` and `wm update`
  - Criteria:
    - `Transaction.delete_folder` removes every file under a folder and then the empty folder, all or nothing with the rest of the transaction
    - `Adapter.skill_folder` names a tool's skills folder; Claude Code's is `.claude/skills`, and `integration.py` names no tool
    - `integration.stage` removes each `wm-*` folder not in `assets.SKILLS` from `.agents/skills` and each listed tool's skills folder, returning a `removed` change per file; other folders are untouched
    - `wm update` prints `removed: <path>` for each, and doesn't ask for a commit when only machine files changed
  - Verify:
    - tests in `tests/services/test_integration.py` for the scenarios "Skill retired" and "The project's own skill"
    - a test in `tests/record/test_store.py` that `delete_folder` is rolled back when the commit fails

## 3. Docs

- [x] 3.1 Update the docs for the single entry and the pruning
  - Criteria:
    - `docs/skills.md` has no `wm-fix` section and says under `wm-propose` how it chooses the path and confirms tiny work
    - `docs/concepts.md`, `docs/getting-started.md`, `docs/smoke-test.md` and the README name `wm-propose` for tiny work and no longer name `wm-fix`
    - the setup docs say `wm init` and `wm update` remove `wm-*` skill folders `wm` no longer ships
    - the docs follow the `waymark-write-docs` skill, and the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `rg wm-fix docs README.md src` finds nothing

## Log

- (accepted) 2026-11-16 fingerprint 563b169b2d57c2c6 items 1.1 1.2 2.1 3.1 by Noah Roberts
- (review) 2026-11-16 pass by wm-reviewer: every item's criteria and every delta scenario hold, wm-propose chooses the path and carries the tiny path with its one-line confirmation, wm-fix is gone from the assets, docs and README, retired wm-* folders are removed all or nothing with a working rollback, and the tests (1136), mypy, ruff, codespell, the docs check and wm check all pass
  - suggestion `tests/adapters/test_integration.py`: the "Skill retired" and "The project's own skill" tests live here, not in `tests/services/test_integration.py` as item 2.1's Verify names; that file doesn't exist and the existing integration tests are in the adapters file
  - suggestion `docs/concepts.md:51`: the reflowed Paths paragraph leaves one line much longer than the rest
  - suggestion `src/waymark/record/store.py:3`: the module docstring now breaks after "then applies", leaving a very short line

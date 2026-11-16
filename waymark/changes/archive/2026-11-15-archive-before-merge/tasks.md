# Tasks

## 1. Archive before the pull request

- [x] 1.1 Describe an archived change with `wm pr`
  - Criteria: `wm pr <change>` (text and `--json`) describes an active change as before, and otherwise the latest archived change of that name, with the same title, why, what changes, specs, items and review, plus an `## Outcome` section and a link to the proposal in the archived folder; a name that is neither active nor archived is refused with the active changes listed; in an atlas, `--repo` works the same for an archived change
  - Verify: tests in `tests/services/test_ci_and_pr.py` for the scenarios "Archived on its branch" and "Neither active nor archived", and one with two archived changes of the same name
- [x] 1.2 Move the archive before the pull request in the guidance
  - Criteria: at the archive step, `wm instructions` says to archive on the change's branch before the pull request, when the human decides, and doesn't mention a merge; `wm check`'s "not archived" warning says the same; `wm-archive` asks the human whether to archive now, on the change's branch, commits the record there and then offers `wm-pr`; `wm-apply` offers `wm-archive` before `wm-pr`; `wm-pr` works on a change archived on its branch; both skills say that if the pull request needs more work, the archive commit is reverted and the change archived again; the planner runs `wm update`
  - Verify: tests in `tests/services/test_agent_interface.py` for the scenario "Built and reviewed", and in `tests/services/test_check.py` for the warning; `uv run --no-sync pytest tests/adapters`
- [x] 1.3 Update the docs
  - Criteria: concepts (the workflow and the archive gate), getting started and the smoke test say the archive is taken on the change's branch before the pull request; the generated docs are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync codespell` and `wm check`

## Log

- (accepted) 2026-11-15 fingerprint 7116ca01da85d5d5 items 1.1 1.2 1.3 by Noah Roberts
- (self-review) 2026-11-15: All three scenarios hold and are tested: wm instructions puts the archive on the change's branch before the pull request with no mention of a merge; wm pr describes the latest archived change of a name with its outcome and archived link (also with --repo in an atlas) and refuses an unknown name listing the active changes. The check warning, wm-archive, wm-apply and wm-pr skills and the docs match. Full checks pass (927 tests, ruff, mypy, codespell, tools.docs --check).
  - warning `src/waymark/services/pr.py`: for a change archived with --override, the Review section says 'Not reviewed yet'; the override reason only shows in the Outcome

# Tasks

## 1. Finding places

- [ ] 1.1 Write a finding's path relative to the project
  - Criteria:
    - a place starting with an absolute path inside the project is written relative to its top folder with forward slashes, followed by the rest of the place as given; both Windows (`C:\...`) and POSIX (`/...`) absolute paths are recognized on every platform
    - in an atlas, a place inside a code repo registered on this machine is written as `<repo>/<path>`
    - a place starting with any other absolute path is refused before anything is written, saying to give the place relative to the project
    - a relative path is written with forward slashes, and a place that isn't a path is written as given
    - this holds for `wm review --self`, `wm verdict`, and a verdict the hook records for a reviewer
  - Verify:
    - `test_scenario_absolute_path_inside_the_project`, `test_scenario_relative_path_with_backslashes`, `test_scenario_code_repo_of_an_atlas` and `test_scenario_absolute_path_elsewhere`, beside the existing finding tests
- [ ] 1.2 Repair the archived findings that hold an absolute path
  - Criteria:
    - the four findings of `waymark/changes/archive/2026-11-17-link-milestone-changes/tasks.md` name their places relative to the project, and nothing else in the file changes
    - no file in `waymark/` holds the path of this machine's checkout
  - Verify:
    - `git diff` of the file shows only the four places changed, and a search of `waymark/` for `project-workspace` finds nothing
    - `wm check` passes

## 2. Docs

- [ ] 2.1 Docs for finding places
  - Criteria:
    - `docs/record.md` says a finding's place is a path relative to the project, or `<repo>/<path>` in an atlas, and that an absolute path is rewritten or refused
    - the CHANGELOG's Unreleased section notes it
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

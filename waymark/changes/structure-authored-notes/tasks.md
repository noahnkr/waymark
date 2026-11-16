# Tasks

## 1. Formats and checks

- [x] 1.1 Read and check the structured Impact
  - Criteria:
    - `parse_proposal` reads `- Specs:`, `- User-visible:` and `- Code:` under `## Impact`, with nested bullets, and `Specs:` into the backticked spec names or `none`
    - `- Specs: none` skips the specs step; the "No spec changes" text no longer does, and the propose step's guidance in `wm instructions` names `- Specs: none`
    - for an active change, a missing line gives `impact-format`, and a spec named without a delta or a delta whose spec isn't named gives `impact-mismatch` naming the spec
    - the proposal template shows the three lines
  - Verify:
    - tests in `tests/record/test_authored_formats.py` and `tests/services/test_check.py` for the scenarios "Impact matches the deltas" and "Delta not named in the impact"
    - `wm check` here
- [x] 1.2 Archive with a structured Outcome
  - Criteria:
    - `wm archive` takes `--built` and `--differs`, and `--outcome` is gone
    - the archived proposal's Outcome holds `- Built: <text>` and `- Differs: <text>`, with `none` when `--differs` is left out
    - a hand-written Outcome without both lines, or `--built` with an Outcome already written, is refused with the form
    - `wm pr` shows both lines
  - Verify: tests in `tests/services/test_archive.py`, `tests/services/test_ci_and_pr.py` and `tests/test_cli.py` for the scenarios "Archived with an outcome" and "Nothing differs"
- [x] 1.3 Number the charter's goals and constraints
  - Criteria:
    - a top-level line in Goals or Constraints, outside comments and fences, that isn't `<n>. <text>` with `n` counting from 1 gives `numbered-list-format` showing `1. <text>`; indented lines continue the item above
    - the charter template numbers its examples
    - this repository's charter is numbered by hand without changing its wording, and `wm check` is healthy here
  - Verify:
    - tests in `tests/record/test_authored_formats.py` for the scenario "Bulleted goal"
    - `wm check` here
- [x] 1.4 Settle decisions and open questions before acceptance
  - Criteria:
    - each decision of an active change's design needs `- Status: proposed|decided` and `- Decided by: human|planner`; a missing or unknown value gives `decision-format` with the values allowed
    - an active change's design needs `## Open questions`, holding `None.` or a list
    - while a decision is `proposed` or a question is listed, the next step stays `design`, with a reason that names each one, so `wm accept` refuses
    - the design template shows both lines and the section
  - Verify: tests in `tests/record/test_authored_formats.py`, `tests/record/test_state.py` and `tests/services/test_lifecycle.py` for the scenarios "Proposed decision" and "Open question"
- [x] 1.5 Keep the new checks to active work
  - Criteria:
    - an archived change with a free-text Impact and Outcome and decisions without `Status:` or `Decided by:` and no `## Open questions` is read without a problem
    - `wm pr` and `wm show` still show such a change
  - Verify:
    - a test in `tests/services/test_check.py` for the scenario "Archived change in an older layout"
    - `wm check` here, with the archived changes in this repository
- [x] 1.6 Read the exploration status from its line alone
  - Criteria:
    - the `Parked:` reader goes; a parked exploration's reason is its Conclusion's text
    - an exploration with `- Status: open` and a `Parked:` Conclusion is open
    - a missing `- Status:` line gives `missing-status`, asking for the line and its values, without naming `wm update`
  - Verify:
    - tests in `tests/record/test_authored_formats.py` for the scenarios "Missing status" and "Parked in the Conclusion only"
    - the existing tests for "Parked exploration" and "Parked without a reason" still pass
- [x] 1.7 Add examples to the templates, show a nested verification, and leave comments out of the fingerprint
  - Criteria:
    - the proposal, delta, design, tasks, charter and exploration templates each hold a comment with a good and a bad example of their content
    - a new change, charter and exploration from those templates give no `wm check` problem from the comments
    - the tasks template shows a `- Verify:` line with a nested list, and the tasks step's guidance in `wm instructions` says `- Verify:` may be a nested list too
    - the fingerprint hashes each part without its comments, so editing or removing a comment leaves acceptance valid
  - Verify:
    - tests in `tests/services/test_setup.py` for the scenario "New proposal"
    - a test in `tests/record/test_authored_formats.py` for the scenario "Nested verification"
    - a test in `tests/record/test_fingerprint.py` that a comment edited after acceptance leaves it valid

## 2. Skills and docs

- [x] 2.1 Show the new layouts in the skills
  - Criteria:
    - `wm-propose` and `wm-update` show the structured Impact, the decision's `Status:` and `Decided by:` lines and the `## Open questions` section, and say that a proposed decision or an open question blocks acceptance
    - `wm-propose` and `wm-update` say `- Verify:` may be a nested list, one step per bullet, like `- Criteria:`
    - `wm-kickoff` writes numbered goals and constraints
    - `wm-archive` drafts `Built` and `Differs` with the human and runs `wm archive --built … --differs …`
  - Verify:
    - the assets tests in `tests/`
    - read each skill against the deltas
- [ ] 2.2 Update the docs and the changelog
  - Criteria:
    - concepts and getting started show the new layouts and `--built`/`--differs`
    - the changelog lists the user-visible changes named in the proposal's Impact, including that `--outcome` is gone
    - the generated docs are regenerated
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - codespell
    - `wm check`

## Log

- (accepted) 2026-11-16 fingerprint e01cf817349f38c2 items 1.1 1.2 1.3 1.4 1.5 1.6 1.7 2.1 2.2 by Noah Roberts

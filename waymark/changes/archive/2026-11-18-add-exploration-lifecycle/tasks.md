# Tasks

## 1. The record

- [x] 1.1 Replace `parked` with `dropped` in the exploration status, its state and the template
  - **Criteria:**
    - `- Status:` reads `open`, `led-to <links>` or `dropped`; `parked` or any other value is an unknown status whose message names `open`, `led-to` and `dropped`
    - a missing status is still `missing-status`, and its message doesn't name `wm update`
    - `ExplorationStatus` has `DROPPED` and no `PARKED`, and the `parked-without-reason` problem is gone
    - the exploration template writes `- Status: open` and its comments describe the three statuses, with a good and a bad example
    - the tests for the old Exploration status scenarios are replaced by tests named after the scenarios New exploration, Parked is not a status and Missing status
  - **Verify:**
    - tests in `tests/record/test_authored_formats.py` (or a new `tests/record/artifacts/test_explorations.py`) for the three scenarios
    - `uv run --no-sync pytest tests/record tests/services/test_check.py`
- [x] 1.2 Read archived explorations, show and list them, and keep their folder in git
  - **Criteria:**
    - `explorations/archive/` is not reported as an unexpected file, and its `<date>-<name>.md` files are read as archived explorations, never checked or fixed; a file whose name doesn't parse is reported as `invalid-name`
    - `wm show <name>` and `wm show <date>-<name>` find an archived exploration and print "Archived on <date>"; its JSON has an `archived_on` date, null for an active one, as `wm.show.change` has
    - `wm ls explorations --archived` lists archived explorations marked archived; without the flag and in `wm context --for explore` they are left out
    - the `wm.show.exploration` and `wm.context.explore` schemas list `open`, `led-to`, `dropped` and their versions are raised
    - `wm init` and `wm update` write `explorations/archive/.gitkeep`, per the four Record folders kept in git scenarios
  - **Verify:**
    - tests in `tests/views/test_views.py` for Show an archived exploration and List with the archived ones
    - tests in `tests/services/test_setup.py` for the four Record folders kept in git scenarios
    - `uv run --no-sync pytest tests/views tests/services/test_setup.py tests/record`
  - 2026-11-18 (reopened) by Noah Roberts
- [x] 1.3 Report a led-to exploration left active, and archive `lighter-workflow`
  - **Criteria:**
    - `wm check` reports an active exploration whose `led-to` targets are all archived or closed as an error, `exploration-not-archived`, that names `explorations/archive/`
    - an archived exploration with `- Status: parked` is not reported
    - `waymark/explorations/lighter-workflow.md` is moved with `git mv` to `waymark/explorations/archive/2026-11-15-lighter-workflow.md`, its relative links re-aimed, and `wm check` is healthy
  - **Verify:**
    - tests in `tests/services/test_check.py` for Exploration whose milestone closed and Archived exploration with an old status
    - `wm check`

## 2. Commands

- [x] 2.1 Add `--from <exploration>` to `wm new change` and `wm new milestone`
  - **Criteria:**
    - the exploration's Status line is set to `led-to` with a link to the new proposal or `milestone.md`, in the same operation that creates it, and no other line of the exploration changes
    - an exploration that already led somewhere gets the new link added after the old ones
    - an unknown or archived exploration is refused with a reason that names it, and nothing is created
  - **Verify:**
    - tests in `tests/services/test_setup.py` for Change from an open exploration, A second change from the same exploration, Milestone from an exploration and Unknown exploration
    - `uv run --no-sync pytest tests/services/test_setup.py tests/test_lifecycle_cli.py`
- [x] 2.2 Move explorations to the archive with their work in `wm archive` and `wm close`
  - **Criteria:**
    - an exploration whose `led-to` targets are all archived or closed after the operation moves to `explorations/archive/<date>-<name>.md` in the same transaction, with its own links re-aimed from there
    - an exploration with a target still active, or one that led to the milestone of the change being archived, stays, with its links re-aimed
    - an archived exploration of the same name and day refuses the whole operation, naming the clash, and changes nothing
  - **Verify:**
    - tests in `tests/services/test_archive.py` for Its only change archived, One of two changes archived and Change in a milestone the exploration led to
    - tests in `tests/services/test_milestones.py` for Its milestone closed and the same-day clash
    - `uv run --no-sync pytest tests/services`
  - **Build:** delegate
  - 2026-11-18 (note) by wm-implementer: Links from other active documents to an exploration moved by wm archive or wm close are not re-aimed; the record asks only for the exploration's own links. A spec or active change linking the exploration would then fail wm check's link check.
  - 2026-11-18 (reopened) by Noah Roberts
- [x] 2.3 Add `wm exploration drop <exploration> --reason "<why>"`
  - **Criteria:**
    - an open exploration gets `- Status: dropped`, the reason as its Conclusion's last paragraph after any text already there, and moves to `explorations/archive/<date>-<name>.md`, in one transaction
    - a `led-to` exploration is refused with a reason that says it ends when its work is archived; an unknown one is refused naming the active explorations; a refusal changes nothing
    - `--reason` is required
  - **Verify:**
    - tests in `tests/services/test_lifecycle.py` for Drop an open exploration, Conclusion kept and Drop an exploration that led to a change
    - a CLI test in `tests/test_lifecycle_cli.py`
    - `uv run --no-sync pytest tests/services tests/test_lifecycle_cli.py`
- [x] 2.4 Refuse an agent's hand edit to an exploration's Status line
  - **Criteria:**
    - an agent edit that adds, changes or removes an active exploration's `- Status:` line is refused with a reason that names `--from` and `wm exploration drop`
    - edits to an exploration's other lines are allowed, and archived explorations aren't guarded
  - **Verify:**
    - tests in `tests/hooks/test_decide.py` for Agent writes led-to by hand and Agent edits the questions
    - `uv run --no-sync pytest tests/hooks`

## 3. Skills and docs

- [x] 3.1 Teach `wm-explore` to resume an exploration, and both skills to use `--from`
  - **Criteria:**
    - `wm-explore` has a first step that, for a named active exploration or a matching one the human confirms, reads it with `wm show`, reports what changed in the record since, and continues from its Questions and Approaches
    - its closing offers for a resumed exploration are do nothing, update or drop it with `wm exploration drop`, a proposal, and a milestone with `--from`; no offer names `wm-fix`, and nothing tells the planner to write a Status line by hand
    - `wm-propose`'s naming step passes `--from <exploration>` when the work comes from a saved exploration
    - both skills keep the section layout the Skill layout requirement holds
  - **Verify:**
    - tests in `tests/test_skills.py` for Started with an exploration's name, Offers for a resumed exploration, Proposal from an exploration and No tiny-path offer
    - `uv run --no-sync pytest tests/test_skills.py tests/adapters`
- [x] 3.2 Update the docs and the CHANGELOG
  - **Criteria:**
    - `docs/concepts.md` describes the three statuses, `--from`, archiving with the work, `wm exploration drop`, resuming with `/wm-explore <exploration>`, and `explorations/archive/` in the record layout, following the `waymark-write-docs` skill
    - `docs/cli.md` and `docs/json.md` are regenerated with `uv run --no-sync python -m tools.docs`
    - `CHANGELOG.md` has the User-visible lines under `## [Unreleased]`
  - **Verify:**
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks: `pytest`, `ruff format --check .`, `ruff check .`, `mypy`, `codespell`
  - 2026-11-18 (reopened) by Noah Roberts

## Log

- 2026-11-18 (accepted) fingerprint 834054d00af42903 items 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2 by Noah Roberts
- 2026-11-18 (review) changes 2.2, 1.2, 3.2; covers 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2 by wm-reviewer: archive and close leave links from the archived change or milestone to its moved exploration dangling (re-aim them, with a test); the show.exploration field is archived_on not archived (rename it or amend the criterion); docs/concepts.md lacks --from, wm exploration drop and resuming, and line 188 wrongly says agents write the exploration Status line.
  - [critical] `src/waymark/services/lifecycle.py _move_explorations`: staged text of the moving change or milestone is parsed at its pre-move path, so its links to an exploration archived in the same operation aren't re-aimed and dangle (e.g. archived proposal.md keeps ../../../explorations/paging.md after the file moved to explorations/archive/2026-02-01-paging.md). This contradicts the design's "no link dangles" and the function's docstring. Parse at the target path, or run the exploration move before the folder rewrite, and add a test where the change or milestone links its exploration.
  - [critical] `src/waymark/views/payloads.py show_exploration`: the JSON field is archived_on (also in views/schemas.py), but criterion 1.2 says archived. Rename it, or have the human amend the criterion to archived_on, which matches wm.show.change.
  - [critical] `docs/concepts.md`: it doesn't describe --from, wm exploration drop or resuming with /wm-explore <exploration> as criterion 3.2 requires, and line 188 still says you and your agents write an exploration's "- Status:" line, which the hooks now refuse.
  - [warning] `src/waymark/record/artifacts/explorations.py with_dropped`: on an open exploration with no Conclusion section, wm exploration drop raises an uncaught StopIteration instead of a refusal. Untested.
- 2026-11-18 (accepted) fingerprint 879fc00b099a5688 items 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2 by Noah Roberts
- 2026-11-18 (review) pass covers 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2 by wm-reviewer: all criteria and scenarios hold; the earlier review's fixes (re-aimed links from the moved change or milestone to its exploration, with tests; criterion amended to archived_on; concepts.md covering --from, drop and resuming; drop refusing a missing Conclusion) are in; pytest, ruff, mypy, codespell, tools.docs --check and wm check all pass.

# Tasks

## 1. Labels

- [x] 1.1 Read every label in both the plain and the bold form, through one labels module
  - Criteria:
    - a new `record/markdown/labels.py` holds the label names, `label_line(name, value, bullet=True)` writing `- **<name>:** <value>`, and a pattern that reads a label line and tells the bold form (colon inside), the plain form and the bold form with the colon outside apart
    - every reader named in the design's Context reads a label in the bold form and in the plain form alike: proposal facts, Impact and Outcome, an item's Criteria, Verify, Repo and Build, a decision's parts, a delta's From, To and Reason, the Repos line, an exploration's Status, a resource's four lines, and the hook's Status-line guard
    - the charter's glossary reads `- **<term>:** <meaning>` as well as `- **<term>**: <meaning>`
    - `wm check` reports nothing new on this record
  - Verify:
    - tests in `tests/record/markdown/test_labels.py` for the three forms
    - a test per artifact in `tests/record/test_authored_formats.py` reading it with bold labels
    - `uv run --no-sync pytest tests/record tests/hooks` and `wm check`
- [x] 1.2 Write every label in the bold form
  - Criteria:
    - the proposal, design, task list, delta, exploration, resource and charter templates write bold labels, the task template writes `- **Build:** planner` first in each item, and the design template writes Options as a nested list
    - `wm new change` writes the Owner, Milestone, After and Path facts bold; `wm archive` writes `- **Built:**` and `- **Differs:**`; `--from` and `wm exploration drop` write `- **Status:**`; `wm new resource` writes its four lines bold; a delta's Repos line is written `**Repos:**`
    - every message that quotes a label shows its bold form, through `label_line`
    - the tests for the scenarios New change, Archived with an outcome, Nothing differs, Change written after another, Planned roadmap line, Change from an open exploration, A second change from the same exploration, Milestone from an exploration, Drop an open exploration and New resource expect the bold lines
  - Verify:
    - `uv run --no-sync pytest tests/services tests/record tests/test_lifecycle_cli.py`
    - `wm check`
  - (note) 2026-11-18 by Noah Roberts: The task template now writes '- **Build:** planner', so tasks.py accepts 'planner' as a build value (an item built by the planner) to keep the template and wm check clean. Item 2.1 still owns the message naming both values, the instructions and the fingerprint.

## 2. Build line and options

- [x] 2.1 Read `planner` as a Build value and follow it
  - Criteria:
    - `- Build: planner` and `- Build: delegate` are read; any other value is reported with a message that names `planner` and `delegate`
    - `wm instructions` tells the planner to build an item whose Build value is `planner` itself, and to start an implementer for `delegate`
    - the fingerprint hashes the Build value; an item without a Build line hashes as before, so no acceptance is withdrawn by this item
    - the tasks-step guidance in `wm instructions` says every item gets a Build line, `planner` or `delegate`
  - Verify:
    - tests in `tests/services/test_check.py` and `tests/record/test_tasks_records.py` for the scenarios Item built by the planner, Tagged item, Unknown build value and Build changed after acceptance
    - `uv run --no-sync pytest tests/record tests/services`
- [x] 2.2 Count a decision's options only as nested bullets
  - Criteria:
    - the split of a one-line Options on `;` and "or" is gone; options are the bullets under the Options line
    - an Options line with text of its own is reported as `decision-options`, asking for one option per bullet; fewer than two bullets asks for at least two
  - Verify:
    - tests in `tests/record/test_authored_formats.py` for the scenarios One option, Options as a list and Options on one line
    - `uv run --no-sync pytest tests/record tests/services/test_check.py` and `wm check`

## 3. Records

- [ ] 3.1 Write records date first, item lists with commas and findings with bracketed severities
  - Criteria:
    - every record, in a change and in a milestone's Log, is written `<date> (<kind>) …`, and read in that order and the old one; `--fix` and the hook's evidence detection recognize both
    - `(accepted)`, `(review)` and `(self-review)` records write their item lists separated by `, `, and a `changes` list followed by `covers` ends with `;`; they are read with commas, and with spaces as before; the record shapes in messages show the new order and the commas
    - findings are written ``- [<severity>] `<place>`: <text>`` and read in that form and the old one; `--fix` recognizes both
    - the tests for the scenarios Blocked item, Resolved item keeps its blocker, Implementer partly done, Log of a plan's changes, Member change archived, Planned roadmap line, Reviewer's verdict, Explicit author, Acceptance in the Log, Item added, Accepted again, Two items named, Item added after a pass, Place with a line number, Self-review with a finding, Absolute path inside the project, Relative path with backslashes and Code repo of an atlas expect the new shapes
  - Verify:
    - `uv run --no-sync pytest tests/record/evidence tests/services tests/test_agent_cli.py`
    - `wm check`

## 4. The record converted

- [ ] 4.1 Teach `--fix` to bold labels and order an item's lines, and convert the active record
  - Criteria:
    - `wm check --fix` rewrites a known label written plain or with the colon outside into `- **<Label>:**`, and puts an item's label lines in the order Build, Repo, Criteria, Verify with their nested lines, naming each file it fixed; it covers `resources/` as well
    - `wm check --fix` has been run on this record; the charter's glossary is moved to `- **<term>:** <meaning>` by hand; each item of this change without a Build line gets `- **Build:** planner`
    - this change's acceptance is withdrawn by the new layout, and the human has accepted it again before the item is ticked
  - Verify:
    - tests in `tests/services/test_fix.py` for the scenarios Layout fixed, Fenced code left alone, Plain label made bold and Item lines put in order
    - `uv run --no-sync pytest tests/services/test_fix.py tests/record/writing`
    - `wm check`
- [ ] 4.2 Rewrite the archive once with an uncommitted script
  - Criteria:
    - a Python script run from the scratchpad, never committed, rewrites every archived change, milestone and exploration: line-start labels into the bold form (and the glossary form where one appears), each record into date-first order, item lists in records into commas with `;` before `covers`, and finding severities into brackets
    - it changes nothing else: one-line Options, items without a Build line and old layouts stay as written
    - every archived change shows its items, records and findings with `wm show <change>`, and `wm check` is healthy
  - Verify:
    - the script's list of changed files, read against `git diff --stat`
    - `wm ls changes --archived`, then `wm show` on each archived change
    - `wm check`

## 5. Old forms removed

- [ ] 5.1 Read labels only in the bold form, and report the rest
  - Criteria:
    - a label written plain, or bold with the colon outside, is no longer read as the label, and `wm check` reports it in the charter, a spec, an active change, an exploration or a resource as `plain-label`, showing the bold form; a glossary line with the colon outside is reported as `glossary-format`
    - the test fixtures across `tests/` use the bold form
    - the tests for the scenarios Plain label, Colon outside the bold (both), Fact without a bullet and Old glossary line pass, and the existing tests for the branches, explorations, milestones, paths and resources requirements and for Structured impact, Settled decisions, Delta sections, Criteria and verification as nested lists and New work only pass with bold labels
  - Verify:
    - `uv run --no-sync pytest`
    - `wm check`
- [ ] 5.2 Require the Build line and the item order, and read only the new record shapes
  - Criteria:
    - `wm check` reports an item of an active change without a Build line as `item-incomplete`, naming `- **Build:**` and the values `planner` and `delegate`, and an item whose label lines are out of order as `item-order`, naming the order
    - records are read only date first, item lists only with commas, and a finding only with a bracketed severity; `wm check` reports an old-shaped record or finding in an active change or an active milestone, showing the shape
    - the tests for the scenarios Item without verification, Item without a Build line, Build line last, Lines in order, Malformed record, Kind before the date, Item list without commas and Severity without brackets pass
  - Verify:
    - tests in `tests/services/test_check.py` and `tests/record/test_tasks_records.py` for those scenarios
    - `uv run --no-sync pytest` and `wm check`

## 6. Skills and docs

- [ ] 6.1 Show the new layouts in the skills and the agent definition
  - Criteria:
    - `wm-propose` tells the planner to give every item a `- **Build:**` line, `planner` or `delegate`, first among its lines, and writes decision options as a nested list
    - the `wm-apply`, `wm-explore`, `wm-onboard`, `wm-propose` and `wm-update` skills and the `wm-implementer` agent quote labels in the bold form and records and findings in their new shapes
    - the skills keep the section layout the Skill layout requirement holds
  - Verify:
    - `uv run --no-sync pytest tests/test_skills.py tests/adapters`
- [ ] 6.2 Update the docs and the CHANGELOG
  - Criteria:
    - `README.md` and `docs/concepts.md`, `getting-started.md`, `multi-repo.md`, `record.md`, `skills.md` and `smoke-test.md` show bold labels, the Build line on every item, options as a list, comma-separated item lists and bracketed severities, following the `waymark-write-docs` skill
    - `docs/cli.md`, `docs/json.md` and the README evidence are regenerated with `uv run --no-sync python -m tools.docs`
    - `CHANGELOG.md` has the User-visible lines under `## [Unreleased]`
  - Verify:
    - `uv run --no-sync python -m tools.docs --check`
    - the full checks: `pytest`, `ruff format --check .`, `ruff check .`, `mypy`, `codespell`

## Log

- (accepted) 2026-11-18 fingerprint ab2018a35172d5de items 1.1 1.2 2.1 2.2 3.1 4.1 4.2 5.1 5.2 6.1 6.2 by Noah Roberts

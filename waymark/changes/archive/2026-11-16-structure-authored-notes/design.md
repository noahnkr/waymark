# Structure authored notes: design

## Context

- **Proposal.** `record/proposal.py` reads the sections, keeps `## Impact` as text, and sets `no_spec_changes` when the Impact says "No spec changes"; `record/state.py` uses it to skip the specs step. `Proposal.outcome` is the Outcome's text, and `accepted_text` leaves the Outcome out.
- **Archive.** `services/lifecycle.py` `archive` takes `outcome`, refuses when there is neither a given outcome nor an `## Outcome` in the proposal, and writes it with `record/edits.py` `set_outcome`. `cli.py` maps `--outcome` to it. `wm pr` prints the Outcome's text.
- **Charter.** `record/charter.py` checks the glossary line by line, skipping comments, fenced and indented lines. Goals and Constraints are kept as text.
- **Design.** `record/design.py` reads `### Decision:` sections under `## Decisions` and requires `Options:`, `Choice:` and `Why:` lines. `collect_sections` reports a section it doesn't know.
- **Acceptance.** `lifecycle.accept` refuses while the next step is a drafting step, quoting the step's reason. The next step comes from `record/state.py`.
- **Archived changes.** `record/changes.py` `load_change` parses every change the same way, and runs the checks that depend on the config only when `archived_on` is None.
- **Explorations.** `record/explorations.py` reads `- Status:` and still reads a `Parked:` Conclusion. A missing status gives `old-layout` with the advice to run `wm update`.
- **Fingerprint.** `record/fingerprint.py` hashes the proposal (without the Outcome), the deltas and each item, in their standard layout, comments included.
- **Templates.** `record/templates/` holds the files `wm new` writes. Their comments say what each section is for.

## Approach

1. **Impact** (`record/proposal.py`, `record/changes.py`, `record/state.py`, the proposal template).
   - `parse_proposal` reads `- Specs:`, `- User-visible:` and `- Code:` from the Impact into `Proposal.impact`, each line's own text plus any nested bullets. `Specs:` is read into a tuple of the backticked names, or empty for `none`.
   - `no_spec_changes` comes from `Specs: none`, not from the "No spec changes" text; the step's guidance in `wm instructions` says so.
   - For an active change, `load_change` reports `impact-format` for a missing line, and `impact-mismatch` naming each spec under `Specs:` without a delta and each delta whose spec isn't named.
2. **Outcome** (`services/lifecycle.py`, `record/edits.py`, `record/proposal.py`, `cli.py`).
   - `archive` takes `built` and `differs`, and `cli.py` maps `--built` and `--differs`; `--outcome` goes. `differs` defaults to `none`.
   - `set_outcome` writes `- Built: <text>` and `- Differs: <text>`. A hand-written `## Outcome` must hold both lines, or `archive` refuses with the form; a given `--built` with an existing Outcome is refused, as `--outcome` is now.
   - `wm pr` keeps printing the Outcome's text, which now holds the two lines.
3. **Numbered goals and constraints** (`record/charter.py`, the charter template).
   - A check like `_check_glossary` runs over Goals and Constraints: each top-level line outside comments and fences must be `<n>. <text>`, with `n` counting from 1. Indented lines continue the item above. Another line gives `numbered-list-format`, which shows `1. <text>`.
   - This repository's charter is numbered by hand in the same item, so `wm check` stays healthy here.
4. **Settled decisions** (`record/design.py`, `record/state.py`, the design template).
   - `DECISION_PARTS` gains `Status` and `Decided by`. `Decision` gets `status` and `decided_by`; another value gives `decision-format` with the values allowed.
   - `## Open questions` joins the required sections. Its body is `None.` or a list; `Design.open_questions` holds the list's items.
   - The next step stays `design` while a decision is `proposed` or a question is listed, with a reason that names each one. `wm accept` then refuses through the existing drafting-step refusal, and `wm status` and `wm instructions` show what is left to settle.
5. **New work only** (`record/changes.py`).
   - The parsers read the new fields where they are and leave them empty where they aren't. The checks that need them (`impact-format`, `impact-mismatch`, the decision's `Status:` and `Decided by:`, the `## Open questions` section) run only when `archived_on` is None, next to `_check_against_config`.
6. **Exploration leftovers** (`record/explorations.py`, `record/state.py`).
   - `_PARKED` and the `Parked:` reader go. A parked exploration's reason is its Conclusion's text.
   - A missing `- Status:` line gives `missing-status`, asking for the line with its three values, and no longer names `wm update`.
7. **Template examples** (`record/templates/`, `record/fingerprint.py`).
   - Each of the six templates gains a comment with a short good and bad example of its content, such as an Impact with the three lines next to one that only says "Some code".
   - The fingerprint hashes each part without its comments, so the planner can delete the examples without withdrawing acceptance.
   - `Verify:` bullets are already read like `Criteria:` bullets (`record/tasks.py` keeps every indented line under an open field), so a nested verification needs no new reader. The tasks template shows one, and the tasks step's guidance in `wm instructions` says `- Verify:` may be a nested list too.
8. **Assets and docs.** `wm-propose`, `wm-update`, `wm-kickoff` and `wm-archive` show the new layouts and the `--built` and `--differs` options. Concepts, getting started and the changelog are updated; the generated docs are regenerated.

## Decisions

### Decision: How the Impact is written
- **Status:** decided
- **Decided by:** human
- **Options:**
  - labeled bullets `- Specs:`, `- User-visible:`, `- Code:`;
  - `### Specs`, `### User-visible` and `### Code` subsections.
- **Choice:** labeled bullets.
- **Why:** They match the proposal's facts and the task item's sub-lines, and stay short on GitHub.

### Decision: What the Outcome holds
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `- Built:` and `- Differs:`;
  - the same plus `- Follow-ups:`.
- **Choice:** `Built` and `Differs`.
- **Why:** What differs from the proposal is what a reader of the archive needs to find; follow-ups belong in the roadmap or a new change.

### Decision: How new work is told from old
- **Status:** decided
- **Decided by:** human
- **Options:**
  - hold only active changes, the charter and explorations to the new layouts;
  - record format 4, with a migration for the mechanical parts.
- **Choice:** active work only.
- **Why:** Most of the new structure can't be made mechanically from old text, and archived changes are already read as they were written.

### Decision: Who may decide
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `human` or `planner`;
  - a person's name.
- **Choice:** `human` or `planner`.
- **Why:** What matters at acceptance is whether the human made the call or is trusting the planner's; names are already in git and the Log.

### Decision: Where an unsettled design stops acceptance
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - keep the next step at `design` while something is unsettled;
  - a separate check in `wm accept`.
- **Choice:** keep the next step at `design`.
- **Why:** `wm accept` already refuses at a drafting step and quotes its reason, and `wm status` and `wm instructions` then point at the same thing without new code paths.

### Decision: Comments and the fingerprint
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - hash each part without its comments;
  - keep hashing comments.
- **Choice:** without comments.
- **Why:** With examples in every template, deleting or editing one would otherwise withdraw acceptance for no change in meaning. An active change accepted before this lands has to be accepted again; none is accepted now.

### Decision: This repository's charter
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - number its goals and constraints by hand, in the item that adds the check;
  - a one-off migration.
- **Choice:** by hand.
- **Why:** It is one file with a dozen or so lines, and there is no migration framework in use to hang it on.

## Open questions

None.

## Risks and trade-offs

- **Archived changes stay uneven.** Old proposals keep free-text Impact and Outcome, and old designs have no decision status. `wm pr` and the views show them as written.
- **`--outcome` goes without a deprecation period.** Anyone scripting `wm archive` must switch to `--built`; only this repository uses Waymark today, so the cost is the `wm-archive` skill and the docs.
- **The `Specs:` check is only as good as the backticks.** A spec named without backticks isn't seen. When no spec on the line is in backticks, the line gives `impact-format`; otherwise the unseen spec's delta gives `impact-mismatch`. Either points at the line.
- **Withdrawn acceptance.** Changing the fingerprint withdraws the acceptance of any active change accepted before it lands. Only this change is active, and it is accepted after the design.

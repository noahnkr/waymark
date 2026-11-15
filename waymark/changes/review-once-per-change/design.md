# Review once per change: design

## Context

- **Items.** `record/tasks.py` reads a `review:` tag per item into `Item.level_tag`. It also reads the records under an item: `(review)`, `(self-review)`, `(reopened)` and `(resolved)`.
- **State.** `record/state.py` `item_state` derives each item's level, whether it is reviewed and whether it is escalated. It counts `changes` verdicts up to `ESCALATE_AFTER_CHANGES`, and any `changes` verdict makes the item need an independent review. `next_step` walks the items and offers apply or review per item.
- **Commands.** `services/lifecycle.py` has `self_review`, `verdict`, `reopen` and `resolve`, all taking an item. `_archive_gate` checks every item's review.
- **Reviewer.** `services/context.py` builds the reviewer's pack per item: the item, the deltas and their scenarios, and the project's context and review rules, without the notes. Building the pack is the delegation gate. `hooks/decide.py` reads the delegation prompt with `_ADDRESS`, as `<change> <item>`, and the agent's ending with `_ITEM_LINE` and `_VERDICT`.
- **Other places.** The fingerprint includes each item's level. `services/pr.py` lists a review per item. `views/` render and describe items with their review.
- **Proposal facts.** `record/proposal.py` reads the fact lines under the title (`Owner`, `Accepted`, `Path`, `Synced`) and ignores others. `Path: short` is the model for a new `Review:` line.
- **`wm` runs this checkout.** `uv tool install --editable` makes the `wm` on PATH this checkout, so the workflow changes under this change as its items land.

## Approach

1. **Proposal.**
   - `record/proposal.py` reads `Review:` into `Proposal.review: ReviewLevel | None`. An unknown value gives `invalid-review-level`, and `independent` on the short path gives `short-path-review`.
   - `Change.review_level(default)` gives the line's value or the default.
   - The fingerprint drops the level from each item's part. It adds the change's effective level, so changing `default_review` still withdraws acceptance from a change without a `Review:` line.
2. **Task list.**
   - `record/tasks.py` reads a `## Review` section, the unnumbered last section, into `Tasks.review_records`, using the same record formats.
   - A `(review)` line with `changes` carries the items to rebuild: `(review) YYYY-MM-DD changes 1.2 2.1: <reasons>`.
   - Findings are sub-lines under a record, `  - critical|warning|suggestion: <place>: <text>`.
   - The parser still reads item-level records and the `review:` tag, so archived changes show as written. An active change with a `review:` tag gives `obsolete-review-tag`, which `wm check` reports as an error.
3. **State.**
   - Replace the review part of `item_state` with `review_state(change, default)`. It gives the level (independent once any `changes` verdict is recorded), whether the change is reviewed, the items to reopen, and the escalation.
   - Items to reopen are those named by the last `changes` verdict that have no `(reopened)` record after it.
   - A `(resolved)` record in the Review section closes everything before it, as it does per item today.
   - `next_step` offers, in this order:
     1. reopen and apply the named items;
     2. apply unticked items;
     3. the review of the change when every item is ticked and the change isn't reviewed;
     4. archive.
   - An item's own escalations (blocked, spec gap) stay per item.
4. **Commands** (`cli.py` and `services/lifecycle.py`).
   - `wm review <change> --self "<summary>" [--finding "<severity>: <place>: <text>"]...`
   - `wm verdict <change> pass|changes|spec-gap "<reasons>" [--items N...] [--finding ...]...`, where `changes` needs `--items`.
   - `wm reopen <change> <item>` is unchanged, and only allowed for an item the last `changes` verdict named.
   - `wm resolve <change> review "<decided>"` resolves the change's review. `wm resolve <change> <item> "<decided>"` stays for blocked items and items with a spec gap.
   - All of them write into the `## Review` section. A critical finding with `pass` or `--self` is refused.
   - `_archive_gate` checks `review_state`.
5. **Reviewer and hooks.**
   - The review pack and gate take a change:
     - The pack holds every item with its criteria and verification but not its notes, the deltas with their scenarios, the design, and the project's context and review rules.
     - The gate requires the change to be accepted, every item to be ticked, and the change to need an independent review that it doesn't have yet.
   - `wm context <change> --for review` takes no item.
   - In `hooks/decide.py`:
     - The reviewer's delegation prompt is the change's name alone.
     - Its ending is `CHANGE: <change>`, then `VERDICT: pass|changes <items>|spec-gap: <reasons>`.
     - Lines `FINDING: <severity>: <place>: <text>` before the ending become findings.
   - The implementer's prompt and ending are unchanged.
6. **Views and PR.**
   - `wm show` (text and JSON) shows the change's review level and its review records and findings, and items no longer carry a review. The schema version is raised because the item fields are removed.
   - `wm instructions` gives the review step's guidance and commands.
   - `wm pr` lists the items without a review each, and adds a line for the change's review.
7. **Assets and docs.**
   - Skills:
     - `wm-apply`: the review step is per change.
     - `wm-propose`: suggest the `Review:` line, not item tags.
     - `wm-update`: the line withdraws acceptance.
     - `wm-onboard` and `wm-pr` to match.
   - `wm-reviewer`: started with `<change>`. It reviews the whole change for completeness, correctness and coherence, and reports findings with severities.
   - Concepts (review levels, the gates, the glossary), getting started, the smoke test, architecture and the README. The regenerated CLI and JSON references.

## Decisions

### Decision: Where the level is set
- Options:
  - a `Review:` line in the proposal;
  - derived by `wm` from the deltas.
- Choice: the proposal line (the human chose it).
- Why: The human sees and accepts it, and can raise or lower it. `wm check` warns about a risky change at `self`, as the old guidance advised.

### Decision: Where the review is recorded
- Options:
  - a `## Review` section in the task list;
  - a separate `review.md`.
- Choice: a section in the task list (the human chose it).
- Why: It keeps the record formats and the parser, and keeps every piece of evidence for a change in one file.

### Decision: What a request for changes reopens
- Options:
  - the items the verdict names;
  - the planner decides.
- Choice: the items named (the human chose it).
- Why: The reviewer knows where the problem is, and naming the items makes the reopening evidence that `wm` writes.

### Decision: Old tags and records
- Options:
  - migrate them with `wm update`;
  - warn and keep them readable;
  - make the tag an error in active changes and still read archived changes.
- Choice: an error in active changes, with archived changes still read.
- Why: This is the only project and nothing is in flight, so a migration would never run. Archived changes are history and are shown as written.

### Decision: How the findings' severities are named
- Options:
  - OpenSpec's `CRITICAL`, `WARNING`, `SUGGESTION`;
  - lowercase `critical`, `warning`, `suggestion`.
- Choice: lowercase.
- Why: They match the record's other values (`pass`, `changes`, `spec-gap`).

## Risks and trade-offs

- **The workflow changes under this change.** Items 1.1 to 1.3 change the record format and the state together. The task list for this change carries no `review:` tags, and its proposal already has `Review: independent`. Until 1.3 lands, `wm` asks for a self-review per item at the default level, and the planner records them. After that, the change gets one independent review at the end.
- **A whole-change review is a bigger read for the reviewer.** That is the point, and it starts once per change instead of once per item.
- **Findings come from free text.** A reviewer may write findings that don't parse. Unparsed `FINDING:` lines are refused with the reason, as a missing ending is.

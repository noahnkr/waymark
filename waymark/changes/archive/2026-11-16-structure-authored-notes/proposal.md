# Structure authored notes

- **Owner:** Noah Roberts
- **Review:** independent

## Why

`tidy-authored-notes` moved what humans write into layouts a migration could make without guessing. What is left adds meaning, so `wm` can check it instead of only reading it:

- a proposal's Impact is free text, so nothing checks that the specs it names are the ones the change has deltas for, and the changelog note is easy to forget;
- an archived change's Outcome is one paragraph, so what differs from the proposal is buried, as in `tidy-authored-notes`;
- the charter's goals and constraints can't be referred to by number;
- a design decision doesn't say who made it or whether it is settled, and a change can be accepted while a question in its design is still open;
- the templates show the headings but not what good content looks like, so drafts vary.

This is the third change on the `record-format-and-skills` milestone.

## What changes

- **Impact:** labeled bullets under `## Impact`: `- Specs:`, `- User-visible:` and `- Code:`. `wm check` compares the specs named under `Specs:` with the change's delta files.
- **Outcome:** `wm archive` takes `--built` and `--differs` and writes them as `- Built:` and `- Differs:` lines under `## Outcome`.
- **Charter:** goals and constraints are numbered lists.
- **Design:** each decision has a `- Status: proposed|decided` and a `- Decided by: human|planner` line, and the design has an `## Open questions` section. `wm accept` refuses a change while a decision is proposed or an open question is listed.
- **Task items:** `- Verify:` may be a nested list, one step per bullet, like `- Criteria:`. The reader already keeps such bullets; the requirement, the template and the guidance now say so, and the requirement is renamed "Criteria and verification as nested lists".
- **Templates:** each template `wm` writes carries a good and a bad example in a comment.
- **Exploration leftovers from `tidy-authored-notes`:** an exploration without a `- Status:` line gives `missing-status`, as the requirement "Exploration status" says, instead of `old-layout` and its advice to run `wm update`, which can't fix it. The old `Parked:` reader in the Conclusion goes, so only the `- Status:` line says an exploration is parked.
- **New work only:** active changes, the charter and open explorations are held to the new layouts. Archived changes are read as they were written, and the record format stays 3.
- **Skills and docs** show the new layouts.

## Non-goals

- Merging a milestone's goal and roadmap: `merge-milestone-files`.
- Checklists per drafting step in `wm instructions`: `add-step-guidance`.
- Rewriting the skills to one layout: `sharpen-drafting-skills`.
- Migrating archived changes, or a new record format.
- Checking `User-visible:` or `Code:` against the code.

## Impact

- **Specs:** `authored-formats` (modified)
- **User-visible:**
  - the proposal's Impact, the archived Outcome, the charter's goals and constraints and the design's decisions change form;
  - `wm archive --outcome` is replaced by `--built` and `--differs`;
  - `wm accept` refuses a change with a proposed decision or an open question;
  - `wm check` reports an Impact that doesn't match the deltas;
  - an exploration without a `- Status:` line is reported as `missing-status`, and a `Parked:` Conclusion no longer parks it.
- **Code:** `record/` (proposal, charter, design, explorations, state, templates), `services/` (lifecycle, setup, check), `cli.py`, `views/`
- Assets and docs: `wm-propose`, `wm-update`, `wm-kickoff`, `wm-archive`; concepts, getting started, the changelog.

## Outcome

- **Built:** The proposal's Impact as Specs, User-visible and Code lines, checked against the deltas; wm archive --built and --differs; numbered charter goals and constraints; design decisions with Status and Decided by lines and open questions that block acceptance; nested Verify; exploration status from its Status line alone; template examples, with comments left out of the fingerprint.
- **Differs:** A Specs line that is empty or names no spec in backticks gives impact-format, not the impact-mismatch the design's risk note describes. Inline code is kept when comments are left out of the fingerprint.

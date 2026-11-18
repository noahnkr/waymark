# Restyle record: design

## Context

- **Labels are read in many places, each with its own pattern.** `record/markdown/outline.py` `_FACT` reads the fact lines under a title, for proposals (`proposal.py`), explorations (`explorations.py`), resources (`resources.py`) and the `Repos` line of specs and deltas (`specs.py`, `deltas.py`). Other labels have their own patterns: `proposal.py` `_IMPACT_LINE` and `_OUTCOME_LINE`, `tasks.py` `_LABELED` and `_FIELD`, `design.py` `_PART`, `deltas.py` `_RENAME_LINE` and `_REASON`, `charter.py` `GLOSSARY_LINE`, and the hook's `evidence.py` `_STATUS_LINE`.
- **Labels are written in many places too.** The templates in `record/writing/templates/`, `services/setup.py` (the Owner, Milestone and After facts), `services/lifecycle.py` (Built and Differs at archive), `explorations.py` `with_led_to` and `with_dropped`, `deltas.py` (the Repos line), and messages across `services/check.py`, `services/instructions.py`, `services/lifecycle.py` and `record/state.py` that quote a label to the user.
- **Records.** `record/evidence/records.py` is the only place a record is built or read. `_arguments` and `_read_arguments` handle the item lists of the `ACCEPTANCE`, `VERDICT` and `COVERS` grammars, which are split on spaces today. `render_finding` and `_FINDING` hold a finding's shape. `writing/layout.py` `_FINDING_LINE` recognizes findings for `--fix`.
- **Build.** `tasks.py` accepts only `delegate` (`DELEGATE`); an item without the line is built by the planner. The fingerprint (`evidence/fingerprint.py`) hashes an item's parsed definition, including the build tag "when present", and hashes the proposal, deltas and design as text in their standard layout (`layout.standard_layout`).
- **Options.** `design.py` `_OPTION_SPLIT` (`;|\bor\b`) counts the options on a one-line Options, so any "or" inside an option counts as a second one.
- **The installed `wm` runs this checkout** (an editable install), so each item's code takes effect on this record as soon as it is written. The record must stay readable, and `wm check` healthy, after every tick.
- **Assets and docs that quote labels:** the `wm-apply`, `wm-explore`, `wm-onboard`, `wm-propose` and `wm-update` skills, the `wm-implementer` agent, `README.md`, and `docs/concepts.md`, `getting-started.md`, `multi-repo.md`, `record.md`, `skills.md` and `smoke-test.md`.

## Approach

1. **One labels module.** A new `record/markdown/labels.py` holds the label names and two helpers: `label_line(name, value, bullet=True)`, which writes `- **<name>:** <value>`, and a `LABEL` pattern that reads a label line and says which form it was in: bold with the colon inside, plain, or bold with the colon outside. Every reader and writer named in Context goes through it, and every message that quotes a label uses `label_line` to show the bold form.
2. **Readers in two steps.** First, every reader accepts both the plain and the bold form, while `wm check` reports nothing new. Once the record is converted (step 7), the plain form is no longer read as the label, and `wm check` reports it as `plain-label`, showing the bold form. This keeps the record healthy after each item is ticked.
3. **Writers.** The templates, `setup.py`, `lifecycle.py`, `explorations.py` and `deltas.py` write the bold form through `label_line`. The task template writes `- **Build:** planner` first in each item. The design template writes Options as a nested list.
4. **Build line.** `tasks.py` reads `planner` and `delegate`. `services/instructions.py` reads an item's Build value instead of the presence of the tag. `wm check` reports a missing Build line (`item-incomplete`, naming the values) and the item's label lines out of order (`item-order`). The fingerprint hashes the build value, so an absent line and `planner` no longer hash the same.
5. **Options.** `design.py` drops `_OPTION_SPLIT` and counts only the nested bullets. An Options line with text of its own is reported as `decision-options`, asking for one option per bullet.
6. **Records and findings.** In `records.py`, `_arguments` joins item lists with `, ` and ends a list with `;` when `covers` follows it. The parser reads a comma-separated list, and in step 2's transition also reads the space-separated one. `render_finding` writes `[<severity>]`, `_FINDING` reads it, and `layout.py` `_FINDING_LINE` follows. The record shapes in `KINDS` show the commas.
7. **`--fix` and the conversion of this record.** `layout.standard_layout` gains two fixes: plain labels made bold (`Fix.LABEL`), and an item's label lines put in order with the lines nested under each (`Fix.ITEM_ORDER`). `--fix` also covers `resources/`. The active record (the charter's glossary, this change's own files, any active exploration) is converted with `wm check --fix`, and the glossary by hand. The archived changes, milestones and explorations are converted by a one-off Python script run from the scratchpad and never committed. It rewrites only line-start labels, item lists in records and finding severities, and leaves everything else, including one-line Options and items without a Build line, as written.
8. **Remove the old forms.** Once the record is converted, the readers drop the plain label form and the space-separated item list, and the plain-label check of step 2 is turned on.
9. **Assets and docs.** The skills, the agent definition, the README and the docs show the new layouts. `wm-propose` tells the planner to give every item a Build line, `planner` or `delegate`. The generated docs are refreshed with `tools.docs`, and the CHANGELOG gets the User-visible lines.

## Decisions

### Decision: Bold form
- Status: decided
- Decided by: human
- Options:
  - colon inside the bold, `**Owner:**`
  - colon outside, `**Owner**:`, as the glossary was
- Choice: colon inside, with the glossary moved to the same form
- Why: it is the usual markdown convention, and one form everywhere is simpler to read and to check.

### Decision: Which lines are labels
- Status: decided
- Decided by: human
- Options:
  - every label line, whether a human or `wm` writes it
  - only the lines humans write
- Choice: every label line
- Why: two styles for the same kind of line would read as a difference that isn't there; the record's own marks (`(kind)` for records, `[severity]` for findings) tell what `wm` wrote.

### Decision: How an item's line order is held
- Status: decided
- Decided by: human
- Options:
  - `wm check` reports it and `--fix` reorders
  - the template only
- Choice: check and fix
- Why: without a check, items drift back to the old order.

### Decision: Finding severity
- Status: decided
- Decided by: human
- Options:
  - bold, `**critical**`
  - capitals, `CRITICAL`
  - parentheses, `(critical)`
  - brackets, `[critical]`
- Choice: brackets
- Why: bold now means a label a human writes, capitals shout, and parentheses would make a finding look like a record and clash with the record-shape check.

### Decision: Item lists in records
- Status: decided
- Decided by: human
- Options:
  - spaces, as today
  - commas, with `;` ending a list that another argument follows
  - commas inside parentheses
- Choice: commas, with `;`
- Why: a review's two lists become easy to tell apart, without the clutter of parentheses; the word `fingerprint` stays, since it says what the digest is.

### Decision: The archive script
- Status: decided
- Decided by: human
- Options:
  - commit it under `tools/`, then delete it in a later commit of the change
  - run it from the scratchpad and never commit it
- Choice: never commit it
- Why: it runs once on the only record there is; the rewritten files are the result that matters.

### Decision: What the archive rewrite covers
- Status: decided
- Decided by: planner
- Options:
  - only what the new readers need: labels, item lists in records, finding severities
  - full conformance, also adding Build lines, ordering item lines and turning one-line Options into lists
- Choice: only what the readers need
- Why: archived changes are read as they were written and aren't checked against the new rules; adding Build lines or splitting options would put words in the archive that nobody wrote, and the old "or" split is the bug this change removes.

### Decision: How the readers move to the new forms
- Status: decided
- Decided by: planner
- Options:
  - accept both forms first, convert the record, then drop the old forms
  - switch every reader, writer and file in one item
- Choice: both forms first
- Why: `wm` on PATH runs this checkout, so a reader that only knows the new form would make the record unreadable until the conversion item is ticked; reading both keeps `wm check` healthy after every item, and the last step leaves one form in the code.

### Decision: The one acceptance this change loses
- Status: decided
- Decided by: planner
- Options:
  - accept that the change is accepted again once, after the layout fix lands
  - keep old fingerprints valid by hashing labels without their bold
- Choice: accept again once
- Why: the standard layout bolds labels once step 7 lands, so the proposal, deltas and design hash differently from the acceptance taken over the old layout, and adding `planner` Build lines changes the items' definitions. Hiding that in the hash would make the fingerprint ignore a change people can see. It is one extra `wm accept`, in the middle of this change only.

## Open questions

None.

## Risks and trade-offs

- **A label missed in one reader.** A reader still on the old pattern would treat a bold label as prose, and the item, fact or decision would go unread. The labels module and a test over each artifact with bold labels guard against it; the plain-label check catches the opposite case.
- **The script misses a line in the archive.** An archived line still in an old form would show wrong in `wm show`. The script reports every file it changed, and every archived change is read once with `wm show` after it runs.
- **Glossary conversion by hand.** Glossary terms aren't known labels, so `--fix` doesn't touch them; the charter has a short glossary, and `wm check` reports any line left in the old form.
- **The exploration on another branch.** `natural-resource-creation` is on the unmerged branch `explore-natural-resource-creation`, with a plain Status line. If it merges after this change, `wm check --fix` makes its line bold.
- **Given up:** reading old layouts. Any record written by an earlier `wm` would need the same conversion; there is no other.

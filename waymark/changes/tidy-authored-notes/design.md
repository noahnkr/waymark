# Tidy authored notes: design

## Context

- **Facts.** `record/outline.py` `parse_facts` reads `Key: value` lines between the title and the first section, with `_FACT` matching a bare `Key:`. `record/proposal.py` reads `Owner`, `Path` and `Review` through it. `services/setup.py` `create_change` builds the fact lines for the proposal template.
- **Charter.** `record/charter.py` keeps the glossary as the section's text without parsing it. Rule headings are matched by `casefold`, and a missing step heading is already allowed.
- **Task items.** `record/tasks.py` reads the build tag with `_TAG` at the end of the item line, and reads `Criteria:`, `Verify:` and `Repo:` sub-lines. A line indented deeper than a sub-line continues the open field, so bullets under `- Criteria:` are already read into it, as text.
- **Deltas.** `record/deltas.py` names its sections with the constants `ADDED`, `MODIFIED` and `REMOVED`. `merge_delta` changes only the lines of the requirements the delta names, and `delta_mismatches` reports conflicts.
- **Explorations.** `record/explorations.py` reads `Parked:` and links from the Conclusion. `record/state.py` derives `ExplorationStatus` from them.
- **Migrations.** `services/migrations.py` runs one step per format number. `services/format_two.py` shows the pattern of a step that reads old files as text with its own patterns.
- **Fingerprint.** It hashes the proposal text, the deltas' text and each item's definition, after the standard layout, so the migration's text changes withdraw the acceptance of an active change.

## Approach

1. **Facts as bullets** (`record/outline.py`, `services/setup.py`, the proposal template).
   - `parse_facts` reads `- Key: value` lines. A bare `Key: value` line for a known key gives `old-layout`, naming `wm update`.
   - `create_change` writes `- Owner: <who>` and `- Path: short`.
2. **Glossary** (`record/charter.py`, the charter template).
   - Each non-blank line of the Glossary section outside comments must match `- **<term>**: <meaning>`; another gives `glossary-format`.
   - The template's step headings are capitalized.
3. **Task items** (`record/tasks.py`, the tasks template).
   - `Build` joins the labeled sub-lines; its only value is `delegate`. `Item.delegate` comes from it.
   - A trailing `` `build: …` `` or `` `review: …` `` tag gives `old-layout`.
   - Bullets under `- Criteria:` are kept as bullets: `Item.criteria` holds the line's own text and each bullet as `- <text>` on its own line. The fingerprint already covers `Item.criteria`.
4. **Deltas** (`record/deltas.py`, `record/specs.py`, the delta template).
   - The section names become `ADDED Requirements`, `MODIFIED Requirements` and `REMOVED Requirements`, matched exactly. The old names give `old-layout`.
   - `RENAMED Requirements` holds `- From:` and `- To:` pairs, read into `Delta.renamed: tuple[tuple[str, str], ...]`. A `From:` without a `To:`, or two renames of one name, is a problem.
   - `merge_delta` renames before it modifies: it rewrites the `### Requirement:` heading line and keeps the block. A rename and a modification of the new name may come in one delta.
   - `delta_mismatches` reports a missing old name or an existing new name. The fingerprint's base parts include the living text of each renamed requirement, so another change archiving into it withdraws acceptance.
5. **Exploration status** (`record/explorations.py`, `record/state.py`, the exploration template).
   - A `- Status:` fact reads `open`, `parked` or `led-to <link>`. `ExplorationStatus` comes from it, not from the Conclusion.
   - Problems: `missing-status`, `unknown-status`, `parked-without-reason` (empty Conclusion), and a `led-to` link that doesn't resolve, through the existing link check.
6. **Format 3 migration** (`services/format_three.py`, `RECORD_FORMAT = 3`).
   - The step reads files as text with its own patterns, like `format_two.py`. It covers every proposal, task list and delta, active and archived, the charter and the explorations:
     - fact lines get a `- ` in front;
     - glossary lines `<term>: <meaning>` become `- **<term>**: <meaning>`;
     - step headings are capitalized;
     - a trailing build tag moves to a `- Build: delegate` line after the item's last sub-line;
     - delta headings are renamed;
     - each exploration gets a `- Status:` line, and `Parked: ` comes off the front of a parked Conclusion.
   - The format 2 readers of these layouts go, as format 1's did.
7. **`--fix`.** `record/layout.py` already handles nested bullets. Nothing new is needed, apart from tests that the new layouts are already in their standard form.
8. **Assets and docs.** The templates and the skills that draft each artifact (`wm-propose`, `wm-update`, `wm-kickoff`, `wm-explore`, `wm-apply`) show the new layouts. Concepts, getting started, the README example and the changelog are updated, and the generated docs regenerated.

## Decisions

### Decision: How a rename is written
- Options:
  - a `## RENAMED Requirements` section with `- From:` and `- To:` pairs;
  - a `Renamed from:` line under a modified requirement.
- Choice: a RENAMED section (the human chose it in the exploration of the milestone).
- Why: It matches OpenSpec's delta sections, and a rename doesn't need to restate the requirement.

### Decision: Where the exploration's state lives
- Options:
  - a `- Status:` fact under the title;
  - keep reading it from the Conclusion.
- Choice: a `- Status:` fact (the human chose it).
- Why: The state is visible at the top and doesn't depend on how the Conclusion is worded. The Conclusion keeps the reason and the link text.

### Decision: Acceptance across the migration
- Options:
  - accept active changes again after the migration;
  - make the fingerprint ignore these layouts.
- Choice: accept again.
- Why: It is what format 2 did, it needs no special case in the fingerprint, and the only active change, `review-added-items`, is not accepted yet.

## Risks and trade-offs

- **The format changes under this change.** Items 1.1 to 1.3 make the readers accept both the old and the new layouts, so this repository stays usable while they are built. Item 1.4 adds the migration, raises the format, and only then reports the old layouts as `old-layout`. It runs `wm update` here, and the human accepts this change again.
- **`review-added-items` sits on its own branch.** When it is picked up, it is rebased onto `main` and migrated by `wm update`.
- **Glossary lines are checked.** A charter with free prose in its glossary fails `wm check` until it is written as a list; the migration turns `Term: meaning` lines into the list and leaves other lines for the human.

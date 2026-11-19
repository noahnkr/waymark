# Add step guidance: design

## Context

- **Instructions.** `services/instructions.py` builds the `wm.instructions` payload (version 1): `_drafting` gives the outputs, reading list and guidance for propose, specs, design and tasks; `_working` gives guidance and commands for the later steps; `_explore` builds the payload for the explore step. `views/render.py` shows `guidance` as "What to do" and the charter's rules as "Rules for this step". `views/schemas.py` describes the payload, with no extra properties allowed; `docs/json.md` is generated from it. Adding a field keeps the version.
- **Checks.** `record/changes.py` runs the checks that hold only for active changes (`_check_against_config`, `_check_impact`, `_check_decisions`). `record/tasks.py` reads each item's `Criteria`, `Verify`, `Repo` and `Build` into `Item`, `None` when absent. `record/design.py` reads each decision's parts into a dict of the line values; nested bullets under `- Options:` are not kept.
- **Skills.** Nine skills in `src/waymark/assets/skills/`, each with a `## Rules` section. Five rules recur across them in different words.

## Approach

1. **Checklists** (`services/instructions.py`).
   - A constant per drafting step, a tuple of `Check(text, enforced_by)`, where `enforced_by` is the tuple of problem codes that `wm check` reports for it, empty when the planner must judge it. The payload's `checklist` is `[{"text": ..., "enforced": bool(enforced_by)}]`; the codes stay internal.
   - Propose:
     - enforced: every section is filled in (`empty-section`); the Impact has its three lines and `Specs:` matches the deltas (`impact-format`, `impact-mismatch`);
     - judged: Why states the problem and why now, not the solution; Non-goals name what a reader might expect and won't get; `User-visible:` names everything users will see change, for the changelog.
   - **Specs:**
     - enforced: every requirement says SHALL (`requirement-without-shall`); every requirement has a scenario with WHEN and THEN (`requirement-without-scenario`, `scenario-incomplete`); a new spec has a Purpose (`delta-without-purpose`); a modified, removed or renamed requirement is in the spec, and an added one isn't (`delta-requirement-missing`, `delta-requirement-exists`);
     - judged: each THEN can be checked by someone who didn't write it; no file names, functions or internals in a requirement.
   - Design:
     - enforced: each decision has Options, Choice, Why, Status and Decided by (`decision-incomplete`, `decision-format`); each decision weighs two options (`decision-options`); Open questions is a list or `None.` (`missing-section`, `open-questions-format`);
     - judged: the design says how, not what, and doesn't repeat the deltas; `Decided by: human` only where the human made the call.
   - Tasks:
     - enforced: every item has Criteria and Verify (`item-incomplete`); items are numbered by section (`item-number`, `section-number`);
     - judged: every scenario in the deltas is covered by some item's criteria; each criterion can be checked; each item can be built from the record alone.
   - Other steps, and explore, give `checklist: []`.
2. **Shared rules** (`services/instructions.py`). A constant `SHARED_RULES`, the five rules of the requirement "Shared rules", put in every payload as `shared_rules`, including the explore step's.
3. **Views** (`views/render.py`, `views/schemas.py`). The text output shows "Shared rules" first, after the step's heading line, then "What to do", then "Checklist", with each check prefixed by a mark: enforced checks by "wm", judged ones by an empty box. The schema gains `checklist` and `shared_rules`; the generated `docs/json.md` is regenerated.
4. **Item check** (`record/changes.py`). For an active change, an item whose `criteria` or `verify` is `None` gives `item-incomplete` on the item's line, naming the missing `- Criteria:` or `- Verify:` line.
5. **Decision check** (`record/design.py`, `record/changes.py`).
   - `Decision` gains `options: tuple[str, ...]`: the bullets indented under `- Options:` when there are any, otherwise the line's value split on ";" and on the word "or", with empty parts and trailing commas dropped.
   - For an active change, a decision with fewer than two options gives `decision-options` on the decision's heading, asking for at least two.
6. **This record.** Only active changes are checked, and the only active change here is this one; its items and decisions meet both new checks.
7. **Skills** (`src/waymark/assets/skills/`). Each skill's `## Rules` drops the rules the shared list covers and starts with "The shared rules from `wm instructions` apply; run `wm instructions explore` to read them when no change is in hand." Rules particular to the skill stay.
8. **Docs.** Concepts says where the checklist and shared rules come from; the changelog lists the new output and the two checks.

## Decisions

### Decision: Checklist next to the guidance
- **Status:** decided
- **Decided by:** human
- **Options:**
  - a separate checklist next to "What to do";
  - turn "What to do" into the checklist.
- **Choice:** a separate checklist.
- **Why:** "What to do" says how to draft; the checklist says what must hold before moving on, and marks what `wm check` already catches.

### Decision: Where the shared rules live
- **Status:** decided
- **Decided by:** human
- **Options:**
  - in `wm`, with the skills dropping their copies;
  - in `wm`, with the skills keeping theirs.
- **Choice:** in `wm`, the skills dropping their copies.
- **Why:** One place to change them, and no drift between nine copies.

### Decision: Which new checks
- **Status:** decided
- **Decided by:** human
- **Options:**
  - items need Criteria and Verify, and decisions need two options;
  - only one of them, or neither.
- **Choice:** both.
- **Why:** Both catch a weak draft mechanically; a scenario per requirement is already checked.

### Decision: How a check knows it is enforced
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - each check names the problem codes that enforce it, and a test holds that each code exists;
  - a plain true or false per check.
- **Choice:** the problem codes.
- **Why:** A check marked enforced can't silently stop being enforced: removing or renaming the code fails the test.

### Decision: Counting inline options
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - split the line on ";" and on the word "or";
  - also split on commas.
- **Choice:** ";" and "or".
- **Why:** Options often contain commas ("in the query, or after sorting"); splitting on them would count one option as two.

## Open questions

None.

## Risks and trade-offs

- **Judged checks are only advice.** Half of each checklist is for the planner to judge; `wm check` can't hold it. The reviewer still checks the change as a whole.
- **Inline options are counted loosely.** A line like "Options: query versus sorting" is one option to `wm`, and is reported; writing the options as bullets avoids that.
- **Shorter skill rules depend on `wm instructions`.** A skill that never runs it would miss the shared rules; every skill's Rules section says to read them.

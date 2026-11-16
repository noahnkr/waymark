# Sharpen agent guidance: design

## Context

- **Context packs.** `services/context.py` builds the implement pack (`_implement_pack`) and the review pack (`_review_pack`), schema `wm.context.implement` and `wm.context.review`, version 2. `_ENDINGS` holds the ending each role must write. `views/render.py` `context_delegated` renders both packs as markdown, with "Rules for this step" and the ending; `views/schemas.py` describes them with no extra properties allowed. Adding a field keeps the version.
- **Instructions.** `services/instructions.py` gives each payload `guidance`, `checklist` and `shared_rules`; `views/render.py` `instructions` shows them.
- **Agents.** `assets/agents/wm-reviewer.md` defines the three severities in one line each under "How you finish"; `assets/agents/wm-implementer.md` has a "Don't guess" rule and no rule for when to stop. `assets/skills/wm-apply/SKILL.md` describes the self-review and its `--finding` severities.
- **Enforcement.** `services/lifecycle.py` already refuses a pass, and a self-review counted as done, with a critical finding.

## Approach

1. **The text** (`services/guidance.py`, new). Two constants, `SEVERITY_RUBRIC` and `STOPPING_RULES`, tuples of strings worded as in the requirements "Severity rubric" and "Stopping rules". One module, so the pack and the instructions can't drift apart.
2. **Packs** (`services/context.py`). The review pack gains `severity_rubric: list(SEVERITY_RUBRIC)`; the implement pack gains `stopping_rules: list(STOPPING_RULES)`.
3. **Instructions** (`services/instructions.py`). Every payload gains `severity_rubric`: the rubric at the review step, an empty list at every other step.
4. **Views** (`views/render.py`, `views/schemas.py`). The packs' markdown shows "## Severity rubric" (review) and "## When to stop" (implement) as bullet lists, just before the ending. The instructions text shows "Severity rubric" after "Checklist" when it isn't empty. The schemas gain the fields; `docs/json.md` is regenerated; versions stay.
5. **Agents and skill** (`assets/`).
   - `wm-reviewer`: under "How you finish", the three one-line severity definitions give way to "Grade each finding by the severity rubric in your pack"; the format lines and the verdict rules stay.
   - `wm-implementer`: a new section, "When to stop", says to follow the pack's stopping rules and end with the result each one names; "Don't guess" stays under what you must not do.
   - `wm-apply`: the self-review says to grade each finding by the severity rubric `wm instructions` gives at the review step.
6. **Docs.** Concepts says where the rubric and the stopping rules come from; the changelog lists them and the new JSON fields.

## Decisions

### Decision: Where the guidance lives
- Status: decided
- Decided by: human
- Options:
  - in the context packs and `wm instructions`, with the agent files pointing at them;
  - in the agent files only.
- Choice: the context packs and `wm instructions`.
- Why: Like the shared rules, they then come from `wm`, reach any agent tool, and the planner's self-review uses the same rubric.

### Decision: The rubric's grading
- Status: decided
- Decided by: human
- Options:
  - grade by what a finding breaks, with the higher severity when torn;
  - keep today's one-line definitions.
- Choice: by what it breaks.
- Why: It ties each severity to something the reviewer can point at, so two reviews grade the same problem the same way.

### Decision: The attempt limit
- Status: decided
- Decided by: human
- Options:
  - stop with `partial` after three attempts at the same failing check;
  - no limit.
- Choice: three attempts.
- Why: A fourth try at the same failure rarely succeeds where three didn't, and the planner is better placed to change course.

### Decision: The rubric for self-review
- Status: decided
- Decided by: human
- Options:
  - the same rubric for a self-review;
  - the independent reviewer only.
- Choice: the same rubric.
- Why: A self-review and an independent one should grade the same finding the same way.

### Decision: One module for both texts
- Status: decided
- Decided by: planner
- Options:
  - a new `services/guidance.py` that both the packs and the instructions import;
  - keep the rubric in `services/context.py` and import it from there.
- Choice: a new `services/guidance.py`.
- Why: Neither service owns the texts; a small module keeps them in one place without one service depending on the other for wording.

### Decision: The field at other steps
- Status: decided
- Decided by: planner
- Options:
  - `severity_rubric` in every instructions payload, empty except at the review step;
  - the field only at the review step.
- Choice: every payload, empty elsewhere.
- Why: The schema stays one shape for every step, as `checklist` does.

## Open questions

None.

## Risks and trade-offs

- **The rubric is still judgment.** `wm` can't check that a finding is graded right; the rubric only makes the grading explainable.
- **Three attempts is a guess at a number.** It can be changed in one place if it proves too few or too many.
- **Agents read longer packs.** The rubric adds about four lines and the stopping rules four; both replace text the agent files used to carry.

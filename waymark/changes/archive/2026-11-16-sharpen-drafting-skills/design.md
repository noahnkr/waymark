# Sharpen drafting skills: design

## Context

- **Skills.** Nine skills in `src/waymark/assets/skills/<name>/SKILL.md`, each with YAML front matter (`name`, `description`), a title, and sections that vary: `Steps` everywhere, then some of `Before you start`, `The loop`, `Common cases`, `Closing offers`, `If the archive is refused`, `When done`, and `Rules` everywhere. `waymark.assets` lists them as `SKILLS` and reads one with `skill(name)`; `wm init` copies them into each agent tool's folder.
- **Guidance.** `services/instructions.py` `_drafting` gives the specs and tasks steps a short "What to do" list; the checklists and shared rules sit beside it (`add-step-guidance`).
- **What the skills already say well.** `wm-apply`'s loop, `wm-archive`'s refusal cases, `wm-update`'s common cases and `wm-explore`'s closing offers are specific and correct; the rewrite keeps their content and moves it into the layout.

## Approach

1. **The layout** (all nine skills). After the front matter and title:
   - `## Role`: who the planner is in this skill, and what the human decides; the opening paragraph each skill has today.
   - `## Inputs`: what to read or run first, such as `wm status`, `wm instructions --change <name> --json`, or the change's name from the human.
   - `## Steps`: numbered, as today.
   - the skill's own sections, renamed to stay specific: `wm-apply` keeps `The loop`; `wm-archive` keeps `If the pull request needs more work` and `If the archive is refused`; `wm-update` keeps `Common cases`; `wm-explore` keeps `Closing offers`.
   - `## Quality bar`: what good output looks like for this skill, in three to five bullets.
   - `## Show the human`: the fixed shape of what the skill shows, as a short template.
   - `## When to stop`: the conditions to stop and hand back, such as a refusal from `wm`, a spec gap, or the human's no.
   - `## Rules`: the shared-rules line, then the skill's own rules, as today.
   - `wm-kickoff`'s `When done` and `wm-apply`'s `Before you start` and `When the step is archive` fold into Inputs, Steps and When to stop.
2. **`wm-propose`.**
   - A step 2, **Questions**, before drafting: list what the record doesn't settle for this change (scope, behavior at the edges, names, what is out), and ask the human, a few at a time, with a recommended answer for each. Write the answers into the artifacts, not only the conversation.
   - A last step before acceptance, **Consistency check**: the Impact's `Specs:` names the deltas (`wm check` holds this); every scenario in the deltas is covered by an item's criteria; the design's approach covers every requirement and adds none; the tasks touch what the Impact's `Code:` names; each decision's choice is what the design does.
   - Show the human: the acceptance summary in a fixed shape: what it does, the deltas (requirement names per spec), the decisions with who made each, the review level, and the items with any delegated.
3. **Fixed summaries** in each skill's Show the human:
   - `wm-apply`: per item, what was built, the checks run and their result, and the commit; after review, the verdict and each finding.
   - `wm-archive`: the outcome's Built and Differs lines for the human to confirm, then what moved.
   - `wm-pr`: the title, the description, and the branch it targets, before asking to open it.
   - `wm-fix`: what changes, why it is tiny, and the requirement it keeps to, before building.
   - `wm-update`: each edit, whether it withdraws acceptance, before making it.
   - `wm-explore`: the closing offers, as today.
   - `wm-kickoff`: the drafted charter section by section.
   - `wm-onboard`: one or two sentences before each step, as today.
4. **`wm-kickoff` interview script.** Steps hold the questions in order, one charter section at a time: the vision (what, for whom, why now); goals (what must be true, each something one could check); non-goals; constraints (platforms, dependencies, budgets, what must never happen); glossary terms; then what the repository shows for Context, stated by the planner for the human to confirm; then rules per step. Each answer is written into its section before the next question.
5. **`wm-explore` method.** Steps: read what the record already says (specs, changes, explorations, milestones touching the idea); state the questions; lay out two or more approaches with what speaks for and against each, naming costs; recommend one and say what would change the recommendation; then the closing offers.
6. **Writing and sizing rules** (`services/instructions.py`). The specs step's guidance gains four lines for writing requirements, and the tasks step's four lines for sizing items, worded as in the requirement "Writing and sizing rules". `wm-propose` and `wm-update` point at them instead of restating them.
7. **The layout test** (`tests/test_skills.py`, new). For each name in `assets.SKILLS`, read `assets.skill(name)`, take its `##` headings in order, and check: the first three are Role, Inputs and Steps; the last four are Quality bar, Show the human, When to stop and Rules; nothing else is in those positions; and the first bullet under Rules is the shared-rules line. A failure names the skill and the heading out of place.
8. **Docs.** Concepts names the skill layout; the changelog lists the rewritten skills and the writing and sizing rules.

## Decisions

### Decision: Split the agent guidance out
- **Status:** decided
- **Decided by:** human
- **Options:**
  - this change covers the skills, and `sharpen-agent-guidance` the reviewer's rubric and the implementer's stopping rules;
  - one change for all eight roadmap items.
- **Choice:** two changes.
- **Why:** The agent definitions and their context packs are a different part of the code; two smaller changes review better.

### Decision: How the layout is held
- **Status:** decided
- **Decided by:** human
- **Options:**
  - a requirement and a test over the shipped skills;
  - a convention only.
- **Choice:** a requirement and a test.
- **Why:** Without a check, the layout drifts back the next time a skill is edited.

### Decision: Where the writing and sizing rules live
- **Status:** decided
- **Decided by:** human
- **Options:**
  - in `wm instructions` for the specs and tasks steps;
  - in the text of `wm-propose` and `wm-update`.
- **Choice:** `wm instructions`.
- **Why:** The milestone's goal says writing rules come from `wm instructions`, so they reach the planner at the step whatever skill it follows.

### Decision: Skill-specific sections
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - allow a skill's own sections between Steps and Quality bar;
  - fold every extra section into Steps.
- **Choice:** allow them between Steps and Quality bar.
- **Why:** `wm-apply`'s loop and `wm-update`'s common cases read better as their own sections than as long numbered steps.

### Decision: Where the layout test lives
- **Status:** decided
- **Decided by:** planner
- **Options:**
  - a new `tests/test_skills.py` over `assets.SKILLS`;
  - inside the integration tests that check `wm init` copies the skills.
- **Choice:** a new `tests/test_skills.py`.
- **Why:** The layout is a property of the shipped files, not of installing them; the test stays fast and says plainly what it holds.

## Open questions

None.

## Risks and trade-offs

- **Longer skills.** Quality bar, Show the human and When to stop add text to every skill. Each is kept to a few bullets, and the shared rules already moved out.
- **A rewrite can lose a rule.** Every step and rule of today's skills is either kept, moved into the layout, or covered by the shared rules; the review reads each skill against its old text.
- **The test holds headings, not content.** A section can be present and weak; the reviewer judges content.

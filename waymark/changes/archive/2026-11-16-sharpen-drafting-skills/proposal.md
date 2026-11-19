# Sharpen drafting skills

- **Owner:** Noah Roberts

## Why

The nine skills each grew their own shape: their sections are named differently, few say what good output looks like, and none says when to stop. Drafts vary with the session. `wm-propose` asks the human questions only when the planner thinks to, and nothing checks that the proposal, deltas, design and tasks agree before acceptance. Summaries for the human are written fresh each time. Kickoff and exploration rely on the planner's own judgment of what to ask and how deep to go. And the rules for writing a good requirement or sizing an item live nowhere.

This is the sixth change on the `record-format-and-skills` milestone. The reviewer's severity rubric and the implementer's stopping rules, which the roadmap first listed here, move to a follow-up, `sharpen-agent-guidance` (the human chose to split them).

## What changes

- **One layout:** every skill has the sections Role, Inputs, Steps, Quality bar, Show the human, When to stop and Rules, in that order; a skill may add its own sections between Steps and Quality bar. A test over the shipped skills holds it.
- **Writing and sizing rules:** `wm instructions` gives the specs step rules for writing requirements and scenarios, and the tasks step rules for sizing items, in "What to do".
- **`wm-propose`:** a question step before drafting, where the planner lists what the record doesn't settle and asks the human; and a consistency check before acceptance across the proposal, deltas, design and tasks.
- **Fixed summaries:** each skill's "Show the human" gives a fixed shape for what it shows, such as the summary before acceptance.
- **`wm-kickoff`:** an interview script, the questions in order, one section of the charter at a time.
- **`wm-explore`:** a deeper method: what the record already says, the questions, two or more approaches with what speaks for and against each, and a recommendation.

## Non-goals

- The reviewer's severity rubric and the implementer's stopping rules: `sharpen-agent-guidance`.
- Checking the skills' content beyond their section layout.
- New `wm check` rules.

## Impact

- **Specs:** `skills` (new), `step-guidance` (modified)
- **User-visible:**
  - the nine skills `wm init` installs are rewritten to one layout, and say what to show the human and when to stop;
  - `wm instructions` for the specs and tasks steps gives writing and sizing rules.
- **Code:** `services/instructions.py`; the layout test in `tests/`
- Assets and docs: all nine skills; concepts and the changelog.

## Outcome

- **Built:** All nine skills share one layout (Role, Inputs, Steps, their own sections, Quality bar, Show the human, When to stop, Rules), held by a test; wm-propose gains a Questions step, a Consistency check and a fixed acceptance summary; wm-kickoff has an ordered interview and wm-explore a fuller method; wm instructions gives the specs and tasks steps the writing and sizing rules.
- **Differs:** The reviewer's severity rubric and the implementer's stopping rules moved to sharpen-agent-guidance, as the human chose.

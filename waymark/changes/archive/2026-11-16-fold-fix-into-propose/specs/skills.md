# Skills

## ADDED Requirements

### Requirement: Shipped skills
`wm init` SHALL install these skills and no others: `wm-kickoff`, `wm-explore`, `wm-propose`, `wm-update`, `wm-apply`, `wm-archive`, `wm-onboard` and `wm-pr`. Work of every size SHALL start from `wm-explore` or `wm-propose`; no skill is for tiny work alone.

#### Scenario: New project
- GIVEN a git repository with no record
- WHEN `wm init` runs for Claude Code
- THEN the installed skills are exactly those eight, and none is named `wm-fix`

### Requirement: Propose picks the path
The `wm-propose` skill SHALL have the planner read the specs and the code and choose the path itself, saying why, without asking the human which path to take:
- **tiny** when the work adds, changes or removes no requirement: the planner shows one line, what it will change and the requirement it keeps to, builds only after the human's yes, then checks, commits and offers a pull request;
- **short** only when the record and the human's words leave nothing to settle;
- **full** otherwise, with every question still open written under the design's `## Open questions`.

When tiny work turns out to change a requirement, the skill SHALL have the planner stop building and draft a change in the same session.

#### Scenario: Path chosen by the planner
- GIVEN the installed `wm-propose` skill
- WHEN its Steps are read
- THEN they tell the planner to choose tiny, short or full from what it found, and to wait for the human's yes before building tiny work

#### Scenario: Open questions
- GIVEN the installed `wm-propose` skill
- WHEN its Steps are read
- THEN they put a change with open questions on the full path, with the questions under the design's `## Open questions`

### Requirement: Explore's closing offers
The `wm-explore` skill SHALL close with four offers: do nothing, save an exploration, start a proposal of any size with `wm-propose`, or start a milestone.

#### Scenario: No tiny-path offer
- GIVEN the installed `wm-explore` skill
- WHEN its closing offers are read
- THEN there are four, and none names `wm-fix`

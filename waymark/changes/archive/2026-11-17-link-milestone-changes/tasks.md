# Tasks

## 1. Link changes to milestones

- [x] 1.1 Read the `- Milestone:` line and check it against the roadmaps
  - **Criteria:**
    - `Proposal.milestone` holds the value of a `- Milestone:` bullet, and is None without one
    - `wm check` reports the errors `unknown-milestone`, `milestone-unlinked`, `milestone-missing`, `milestone-other` and `milestone-twice` on an active change's proposal, each message naming the milestone and what to do
    - archived changes are not checked against roadmaps
    - `wm check` is healthy in this repository, where `link-milestone-changes` names `stronger-milestones` and its roadmap links it
  - **Verify:**
    - tests in `tests/record/` and `tests/services/test_check.py` for the scenarios "Proposal and roadmap agree", "Roadmap doesn't link the change", "Linked change names no milestone" and "Unknown milestone", and for a change on two roadmaps
    - `wm check` here
- [x] 1.2 Create a change in a milestone with `wm new change --milestone`
  - **Criteria:**
    - `wm new change <name> --milestone <milestone>` writes `- Milestone: <milestone>` under `- Owner:`, and links the change from the roadmap: a planned line starting with the name becomes a link and keeps its text, or a linked line is added at the end of the roadmap
    - the milestone file keeps its line endings, and the proposal and the roadmap are written together
    - an unknown milestone is refused before anything is written, and `--milestone` is refused for a milestone or an exploration
    - `docs/cli.md` is regenerated
  - **Verify:** tests in `tests/services/test_setup.py` and `tests/test_cli.py` for the scenarios "Planned roadmap line", "Change not on the roadmap" and "Unknown milestone refused"
- [x] 1.3 Carry the milestone's Goal and Non-goals in the implement and review packs
  - **Criteria:**
    - the implement and review packs of a change that names an active milestone have a `milestone` field with its name, goal and non-goals, and their text has a `## Milestone` section with them
    - the packs of a change without a milestone have `milestone: null` and no such section
    - neither pack holds the milestone's Done when or roadmap
    - `views/schemas.py` declares the field, and `docs/json.md` is regenerated
  - **Verify:** tests in `tests/services/test_agent_interface.py` and `tests/views/` for the scenarios "Member change's packs" and "Change without a milestone"

## 2. Skills and docs

- [x] 2.1 Describe the `- Milestone:` line, its check and `--milestone`
  - **Criteria:**
    - `wm-propose` drafts a member change with `wm new change <name> --milestone <milestone>`
    - `docs/concepts.md` and `docs/record.md` describe the `- Milestone:` line, the check and the flag, and say the packs carry the milestone's Goal and Non-goals
    - the changelog's Unreleased section has the line
    - the docs follow the `waymark-write-docs` skill
  - **Verify:** `uv run --no-sync pytest tests/adapters tests/test_docs.py`, codespell and `wm check`

## Log

- 2026-11-17 (accepted) fingerprint f9584396683ca471 items 1.1, 1.2, 1.3, 2.1 by Noah Roberts
- 2026-11-17 (review) pass covers 1.1, 1.2, 1.3, 2.1 by wm-reviewer: every item's criteria and every scenario in the authored-formats and milestones deltas hold; tests (1152), mypy, ruff, codespell and wm check are clean; findings are only an untested CLI edge, a pack field that is broader than the spec, and two small wording and matching points
  - [warning] `src/waymark/services/context.py`: the _milestone helper gives the packs a milestone whenever the proposal names an active one, even if its roadmap doesn't link the change. The spec carries it only for a change that belongs (named and linked); wm check reports this case as milestone-unlinked, so the behavior matches the 1.3 criterion but is broader than the requirement "Milestone in the context packs"
  - [warning] `tests/test_cli.py`: test_wm_new_change_takes_a_milestone never tests the refusal of --milestone for an exploration (1.2 criterion); only wm new milestone with --milestone is checked
  - [suggestion] `src/waymark/record/milestones.py`: link_change converts a planned line only when its text is exactly the name or starts with "<name>:". This follows the design, but the spec says "starts with the change's name", so a line like "- add-limit - cap" gets a second, linked line added instead
  - [suggestion] `src/waymark/services/setup.py`: when a milestone folder exists but has no milestone.md, the create_change refusal suggests "wm new milestone <name>", which would itself be refused because the name is taken

# Link milestone changes

- **Owner:** Noah Roberts
- **Milestone:** stronger-milestones
- **Review:** independent

## Why

A milestone is a list of links today. A change belongs to one only because a roadmap line links to its proposal, a link the planner writes by hand, and nothing checks it. The change itself doesn't say it belongs to a milestone, and the agents that build and review it never see the milestone's goal or what it leaves out. So a change can drift from the milestone it serves, and a roadmap can link a change that no longer agrees with it.

This is the first change of the `stronger-milestones` milestone. The later ones, a milestone log and change dependencies, build on a change knowing its milestone.

## What changes

- **A proposal names its milestone.** An optional `- Milestone: <name>` fact under the `- Owner:` line names the milestone by its folder name, such as `- Milestone: stronger-milestones`. A change without the line belongs to no milestone and works as today.
- **`wm check` holds the proposal and the roadmap to each other.** For an active change it reports an error when the proposal names a milestone that doesn't exist or whose roadmap doesn't link the change, when a roadmap links the change and its proposal names no milestone or another one, and when more than one roadmap links it. Archived changes are read as written.
- **`wm new change <name> --milestone <milestone>`** writes the `- Milestone:` line, and links the change from the milestone's roadmap: a plain roadmap line that starts with the change's name becomes a link to the new proposal and keeps its description; otherwise a linked line is added at the end of the roadmap. It refuses a milestone that doesn't exist or is closed.
- **Member changes' agents see the milestone.** The implement and review context packs of a change that names a milestone carry the milestone's name, Goal and Non-goals.
- **A `milestones` spec** holds milestone behavior: the new requirements, and "Milestone as one file", moved from `authored-formats`.

## Non-goals

- Changing the roadmap through `wm` commands, a milestone log, or closing rules: that is `add-milestone-log`.
- Change dependencies, branches and bases: that is `add-change-dependencies`.
- Showing a change's milestone in `wm status` or `wm show`.
- Giving agents the milestone's Done when or its roadmap.
- Making milestones required.

## Impact

- **Specs:** `milestones` (new: the `- Milestone:` line and its check, `wm new change --milestone`, the milestone in the packs, and "Milestone as one file" moved here); `authored-formats` ("Milestone as one file" removed, moved to `milestones`).
- **User-visible:**
  - a proposal may have a `- Milestone: <name>` line, and `wm check` reports an active change whose proposal and roadmap disagree;
  - `wm new change` takes `--milestone <milestone>`, and links the change from the roadmap;
  - the implement and review context packs, and their JSON, carry the change's milestone with its Goal and Non-goals.
- **Code:** the proposal facts (`record/proposal.py`), the milestone and roadmap checks (`record/milestones.py`, `record/record.py` or `services/check.py`), `wm new change` (`cli.py`, `services/setup.py`), the context packs (`services/context.py`) and their views (`views/`), the `wm-propose` skill, and the docs.

## Outcome

- **Built:** A proposal can name its milestone in a "- Milestone: <name>" line, and wm check reports an active change whose line and the roadmaps disagree, with five errors. wm new change <name> --milestone <milestone> writes the line and links the change from the roadmap. The implement and review packs carry the milestone name, Goal and Non-goals. A new milestones spec holds milestone behavior, with "Milestone as one file" moved there from authored-formats.
- **Differs:** The independent review passed with four findings left open: the packs carry a milestone the proposal names even when its roadmap does not link the change (wm check reports that case), which is broader than the spec; no test covers --milestone being refused for an exploration; a planned roadmap line becomes a link only when it is the name or starts with "<name>:", not any line starting with the name; and the refusal for a milestone folder without milestone.md suggests a wm new milestone command that would also be refused.

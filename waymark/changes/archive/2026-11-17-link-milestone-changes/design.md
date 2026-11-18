# Link milestone changes: design

## Context

- `record/proposal.py` reads the proposal's facts with `parse_facts(doc, {OWNER, PATH, REVIEW}, ...)`. Any other bullet line above the first section is read as prose, so a `- Milestone:` line passes today and means nothing.
- `record/milestones.py` reads each milestone's roadmap entries, with the link target of each line. `record/state.py` resolves a target into a change folder (`_member`), and `milestone_state` counts a milestone's members and progress. Nothing goes the other way, from a change to its milestone.
- `services/check.py` turns record-wide state into findings, with `Severity.ERROR` or `WARNING`. Archiving already rewrites a roadmap link to the archived change.
- `services/setup.create_change` writes the proposal from the template in one `Transaction`. `cli.py` passes `--short` and `--owner` to it.
- `services/context.py` builds the implement pack (`_implement_pack`) and the review pack (`_review_pack`); `views/render.py` prints them, and `views/schemas.py` declares their JSON. Adding a field keeps a payload's version.
- "Milestone as one file" lives in `authored-formats` today, and its checks in `record/record.py` and `record/milestones.py`; moving the requirement to the new spec moves no code.

## Approach

1. **The fact.** `parse_proposal` reads `MILESTONE = "Milestone"` with the other facts, and `Proposal` gains `milestone: str | None`, the bullet's value.
2. **Membership and its check.** `record/state.py` gains `milestone_links(record)`: for each active change, the active milestones whose roadmap links its proposal, using `_member`. A new `milestone_findings(record)` in `services/check.py` compares each active change's `milestone` with those links and reports errors on the proposal:
   - `unknown-milestone`: the name isn't an active milestone's folder;
   - `milestone-unlinked`: the named milestone's roadmap doesn't link the change;
   - `milestone-missing`: a roadmap links the change and the proposal has no `- Milestone:` line; the message names the line to add;
   - `milestone-other`: a roadmap links the change and the proposal names a different milestone;
   - `milestone-twice`: more than one roadmap links the change.
   Archived changes are skipped. `check_record` adds these findings.
3. **`wm new change --milestone`.** `cli.py` adds `--milestone <name>` to `wm new`, for a change only, as `--short` is. `create_change` refuses a name that isn't in `record.milestones`, before writing anything. It writes `- Milestone: <name>` after `- Owner:` and, in the same transaction, the milestone's `milestone.md` with its roadmap edited: the first entry with no link whose text is the change's name or starts with `<name>:` becomes `- [<name>](../../changes/<name>/proposal.md)` plus the rest of the line; with no such entry, that link line is added after the last line of the `## Roadmap` section. The file's line endings are kept.
4. **The packs.** A helper in `services/context.py` returns `{"name", "goal", "non_goals"}` for a change whose proposal names an active milestone, or None. Both packs carry it as `milestone`; the payload version stays. `views/schemas.py` declares it as nullable, and `views/render.py` prints a `## Milestone` section after the project context: the name, then its Goal and its Non-goals.
5. **Skills and docs.** `wm-propose` drafts a member change with `wm new change <name> --milestone <milestone>`. `docs/concepts.md` and `docs/record.md` describe the `- Milestone:` line, the check and the flag; the changelog gets its line.

## Decisions

### Decision: How the proposal names its milestone
- Status: decided
- Decided by: human
- Options: the milestone's folder name; a Markdown link to its `milestone.md`
- Choice: the folder name, `- Milestone: stronger-milestones`
- Why: it is easy to type and to check, and nothing rewrites it when a change is archived or a milestone closed

### Decision: How strict the check is
- Status: decided
- Decided by: human
- Options: errors both ways; an error one way and a warning the other; warnings only
- Choice: errors both ways, for active changes only
- Why: a roadmap and a proposal that disagree leave the change's milestone unclear, which is what this change is meant to stop. Unmerged branches with hand-linked changes add the line when they are rebased

### Decision: What `--milestone` does to the roadmap
- Status: decided
- Decided by: human
- Options: link a planned line or add a new one; only link an existing planned line
- Choice: link a planned line that starts with the change's name, or add a linked line at the end
- Why: the usual case, a planned line, keeps its description, and a change not planned yet still joins the milestone in one command

### Decision: Where "Milestone as one file" lives
- Status: decided
- Decided by: human
- Options: move it to the new `milestones` spec; leave it in `authored-formats`
- Choice: move it, unchanged
- Why: the milestone asks for milestone behavior in one spec; the move removes a requirement, so the change is reviewed independently

### Decision: A change on two roadmaps
- Status: decided
- Decided by: planner
- Options: an error; a warning; allow it and use the proposal's line
- Choice: an error
- Why: the proposal names one milestone, so a second roadmap linking the change always disagrees with it

### Decision: Where the check runs
- Status: decided
- Decided by: planner
- Options: in `record/record.py` with the per-file problems; in `services/check.py` as findings over the whole record
- Choice: `services/check.py`, with the links derived in `record/state.py`
- Why: the check compares two files, a proposal and roadmaps, as the other record-wide findings in `check.py` do, and `state.py` already resolves roadmap links

### Decision: The milestone in the packs
- Status: decided
- Decided by: planner
- Options: a `milestone` field with name, goal and non-goals; the whole `milestone.md`; only the name, for the agent to look up
- Choice: a `milestone` field with name, goal and non-goals, null without one
- Why: the milestone asks for its Goal and Non-goals only, and an agent shouldn't need another command to get them; a new field keeps the pack's version

## Open questions

None.

## Risks and trade-offs

- The unmerged branches `add-resources`, `flatten-charter-rules` and `add-spec-background` link their changes from the `context-beyond-the-code` roadmap by hand. After rebasing onto this change, `wm check` reports `milestone-missing` on each until its proposal gets a `- Milestone:` line. They aren't accepted yet, so nothing is withdrawn.
- Editing the roadmap line by text is fragile with hand-formatted lines, such as a checked box or extra links. Only a plain line with no link is converted; anything else gets a new line added, which `wm check` then shows as a second line to clean up by hand.
- An archived change's proposal may name a milestone that was closed since; it isn't checked, so that is never reported.

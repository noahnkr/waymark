# Fold fix into propose: design

## Context

- The skills are tool-neutral files in `src/waymark/assets/skills/<name>/SKILL.md`, listed in `assets.SKILLS`. `integration.integration_files` renders each into the shared folder `.agents/skills/`, and each adapter's `files()` adds its own copies; Claude Code's go to `.claude/skills/`.
- `integration.stage` is the one place that stages these files. `setup.init_project` (new project) and `integration.setup_machine` (`wm init` in a clone, and `wm update`) both call it, and `wm update` prints every `FileChange` whose status isn't `unchanged` as `<status>: <path>`.
- Nothing removes a file `wm` stopped shipping. `Transaction.delete` stages a file's removal, all or nothing with the rest of the transaction, but leaves its folder behind.
- Constraint 6: only `src/waymark/adapters/` may name an agent tool, and only `record/` and `assets/` touch files.
- `wm-propose`'s step 1 asks the human for the path and hands tiny work to `wm-fix`; its rules say "Write no code in this skill". `wm-fix`'s steps (check it is tiny, ask, branch, build, check, commit, offer a pull request) are what the tiny path keeps.
- `tests/test_skills.py` uses `wm-fix` as the skill in its "section out of place" scenario.

## Approach

**Skills.**
- `wm-propose` step 1 becomes **Investigate and choose the path**: read the specs the work touches and the code, then choose tiny, short or full by the rules in the `skills` delta and say why in one or two lines. No question to the human about the path.
- A new section `## The tiny path`, between Steps and Quality bar, carries `wm-fix`'s steps: the one-line confirmation ("Tiny: <what changes>; keeps <requirement>") and the wait for a yes, then branch, build, check, commit and the offer of a pull request with a description that says why no requirement changes. If building shows a requirement changes, stop building and go back to step 1 on the short or full path.
- Step 2 (Questions) stays for asking what the human's words and the exploration leave open, but a question left unanswered moves the change to the full path and goes under the design's `## Open questions`; the short path is chosen only when no question is left.
- The rules become "Write code only on the tiny path"; "Don't merge" moves over from `wm-fix`; the When to stop entry "The work is tiny: hand over to `wm-fix`" is removed. Show the human gains the tiny line and the pull request text.
- `wm-explore`'s closing offers become four: do nothing, save an exploration, start a proposal (any size, `wm-propose` chooses the path), start a milestone.
- `wm-onboard` and `wm-update` name `wm-propose` where they named `wm-fix`.
- `wm-fix` is deleted from `assets/skills/` and from `assets.SKILLS`.

**Pruning.**
- `Adapter` gains `skill_folder: str | None = None`, the folder its `files()` copies the skills into; Claude Code's is `.claude/skills`.
- `Transaction.delete_folder(relative)` stages every file under a folder for deletion and, at commit, removes the folder once it is empty; a rollback restores the files.
- `integration.stage_retired(transaction, files, tools)` lists the entries of `.agents/skills` and each listed tool's `skill_folder` through `RecordFiles.entries`, and for each folder named `wm-*` that isn't in `assets.SKILLS`, stages `delete_folder` and returns one `FileChange(<path of each file>, "removed")`.
- `integration.stage` calls `stage_retired` after staging the current files, so `wm init` (both ways) and `wm update` prune in the same transaction they write in, and `wm update` lists `removed: <path>` lines with no extra code.

**Docs.** `docs/skills.md` drops its `wm-fix` section and describes the path choice under `wm-propose`; `docs/concepts.md`, `docs/getting-started.md`, `docs/smoke-test.md` and the README name `wm-propose` for tiny work.

## Decisions

### Decision: Who chooses the path
- Status: decided
- Decided by: human
- Options: the human picks it in `wm-propose`, as today; `wm-propose` chooses it from what it finds
- Choice: `wm-propose` chooses it
- Why: the conversation belongs in `wm-explore`; once the human asks for the work, the size follows from what the specs and the code show

### Decision: Approval of tiny work
- Status: decided
- Decided by: human
- Options: picking the offer in `wm-explore` counts as the yes; a one-line confirmation in `wm-propose` before building; the pull request is the only approval
- Choice: a one-line confirmation before building
- Why: `wm-propose` can be started without `wm-explore`, and the `paths` requirement asks for the human's yes in the session before tiny work; one line costs one message

### Decision: Open questions on a small change
- Status: decided
- Decided by: human
- Options: a short change carries them as a gap; any change with open questions takes the full path
- Choice: the full path
- Why: the design's open questions already block acceptance; a short change has nowhere to hold them

### Decision: Removing retired skills
- Status: decided
- Decided by: human
- Options: leave stale skills to the user; `wm init` and `wm update` remove `wm-*` folders `wm` no longer ships
- Choice: remove them
- Why: the `.gitignore` block already claims `wm-*` skill folders as `wm`'s, so nothing of the user's is lost, and a stale `/wm-fix` would contradict the new flow

### Decision: Where a tool's skills folder is named
- Status: decided
- Decided by: planner
- Options: a `skill_folder` attribute on the adapter; parse it from the adapter's `ignored` patterns; name `.claude/skills` in `integration.py`
- Choice: a `skill_folder` attribute
- Why: constraint 6 keeps tool names in the adapters, and parsing ignore patterns would tie pruning to their spelling

### Decision: How a folder is removed
- Status: decided
- Decided by: planner
- Options: `Transaction.delete_folder`, committed with the rest; `shutil.rmtree` in the service
- Choice: `Transaction.delete_folder`
- Why: constraint 6 keeps file access in `record/`, and constraint 5 asks that a multi-file operation completes or leaves everything as it was

## Open questions

None.

## Risks and trade-offs

- A folder the user named `wm-something` by hand in a skills folder is removed. The `.gitignore` block already treats `wm-*` as `wm`'s, and the docs will say so.
- `wm-propose` grows by the tiny path's steps; the section keeps them apart from the drafting steps.
- `wm doctor` doesn't report a retired skill before `wm update` runs; `wm init` and `wm update` remove it.
- The choice of path rests on the planner's reading; a wrong "tiny" is caught by the confirmation line and by the stop when a requirement turns out to change.

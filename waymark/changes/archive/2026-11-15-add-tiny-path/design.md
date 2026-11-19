# Add tiny path: design

## Context

- **Edits outside a change already work, except in an atlas.**
  - In a single repository, the hooks let the planner edit any file but a spec, and spec edits are refused outside archive and sync.
  - In an atlas, `hooks/decide.py` (`_outside_record`) limits the planner's edits in a code repo to the repos in `editable_repos`: those the next item of an accepted change names. Implementers have the same limit.
- **The short and full paths already exist and are checked.** `Path: short` is read by `record/proposal.py`. `record/changes.py` reports a design on the short path (`short-path-design`) and an independent level on the short path (`short-path-review`). `record/state.py` asks for a design before tasks on the full path. The new `paths` spec writes down behavior that exists; its tests mostly exist too.
- **Skills.** `assets/__init__.py` lists the shipped skills. The adapters copy each one, and `tests/adapters/test_claude_code.py` counts eight. `wm-propose` asks "whether this is a small change" and offers only the short path.
- **Specs guidance.** `services/instructions.py` gives the specs step four lines of guidance, none about what belongs in a requirement.

## Approach

1. **Atlas edit rule.**
   - In `_outside_record`, a planner edit in a code repo is allowed.
   - The implementer branch is unchanged.
   - `editable_repos` is used only for implementers again; its docstring says so.
   - The planner's refusal text and its two tests are replaced by tests for the three scenarios of the modified requirement.
2. **The `wm-fix` skill** (`assets/skills/wm-fix/SKILL.md`), listed in `assets/__init__.py`:
   1. Confirm the work adds, changes or removes no requirement. Check against `wm show <spec>` when unsure.
   2. Say why to the human, and wait for their yes.
   3. Build on a branch named for the fix. Run the checks it touches, then the full checks.
   4. Commit with a conventional message, and offer a pull request, which the planner opens only on the human's yes.
   5. Stop and hand over to `wm-propose` if a requirement turns out to change.

   The skill writes nothing to the record. In an atlas, the session started in the atlas stays the one place work is done from, tiny fixes included. A fix may touch several code repos. It uses a branch of the same name in each repo it touches, commits in each, and offers one pull request per repo, each linking to the others, as changes do.
3. **`wm-propose` step 1** asks which path fits: tiny (no requirement changes, so hand over to `wm-fix`), short (no design) or full. `wm-explore`'s closing offers gain "fix it on the tiny path", and `wm-onboard` mentions the paths.
4. **Specs guidance.** The specs step in `wm instructions` gains one line: requirements say what the system does, as a user or another program sees it; files the user doesn't touch, internals and mechanisms go in the design. `wm-propose` says the same, and the charter's `### specs` rules get it for Waymark.
5. **Tests for the `paths` spec.** Add a hook test for "Code edited outside a change" and "Spec edited outside a change", and a test for "Nothing recorded". Name the existing short-path tests after the scenarios, or point to them.
6. **Charter and docs.**
   - The charter's goals for the two approvals and the light paths.
   - Concepts: a "Paths" section with the three paths, and the roles table's atlas wording.
   - Getting started, the multi-repo guide (the planner may edit any code repo), the smoke test (one tiny fix) and the README's "Light for small changes".

## Decisions

### Decision: How tiny work is approved
- **Options:**
  - the human's yes in the session;
  - a record entry that `wm` writes.
- **Choice:** the human's yes in the session (the human chose it).
- **Why:** Tiny work changes nothing the record describes, so a record entry would be paperwork. The merge is the second approval.

### Decision: What qualifies as tiny
- **Options:**
  - no requirement changes;
  - no requirement changes and a size limit;
  - docs and typos only.
- **Choice:** no requirement changes (the human chose it).
- **Why:** The specs are what Waymark protects. A large refactor that changes no behavior needs no spec work, and a one-line change that does needs a change.

### Decision: Planner edits in an atlas
- **Options:**
  - keep the limit to the item being built, and have no tiny path in an atlas;
  - let the planner edit any code repo.
- **Choice:** let the planner edit any code repo (the human chose it).
- **Why:** The planner already edits any file in a single repository. The limit kept an atlas stricter for no reason the record holds. Implementers keep their limit, since they are started for one item.

### Decision: A separate skill for the tiny path
- **Options:**
  - a `wm-fix` skill;
  - a branch inside `wm-propose`.
- **Choice:** a `wm-fix` skill.
- **Why:** `wm-propose` writes no code by rule, and tiny work is mostly code. A skill of its own also lets the human start the tiny path directly.

## Risks and trade-offs

- **Calling work tiny when it changes behavior.** Nothing in `wm` can tell. The skill asks the planner to check the specs and to say why, and the human says yes or no. The merge review is the backstop.
- **An atlas loses a guard rail.** The planner may now touch a code repo with no change in flight. That matches the single-repository case. The record stays protected, because specs can only change through a change.

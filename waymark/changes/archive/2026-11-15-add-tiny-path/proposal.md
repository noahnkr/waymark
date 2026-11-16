# Add tiny path

- Owner: Noah Roberts
- Review: independent

## Why

Waymark has two routes for a change: the short path (a proposal and a task list) and the full path (with a design). Both still mean a change folder, an acceptance, a review and an archive. `check-release-pin`, about 30 lines in one tool, went through every one of those steps. Much everyday work doesn't touch what the system does at all: a typo, a docs fix, a bug where the code disagrees with a spec, a refactor or a dependency bump. For that work, the record has nothing to say and nothing to keep.

The exploration `lighter-workflow` asked for paths that scale with the size of the change, and this is the third change on that milestone. It also asked that specs stay functional: requirements say what the system does, while files, internals and mechanisms belong in the design. Waymark's own specs mostly do, but a few lines describe internals or are out of date.

## What changes

- **A tiny path for work that changes no requirement.** It needs no change folder.
  - The planner says why the work is tiny (it adds, changes or removes no requirement) and builds it only after the human agrees in the session.
  - It runs the checks, commits with a conventional message, and offers a pull request.
  - Nothing is written to the record. The human's second approval is the merge.
  - If the work turns out to change a requirement, it stops and becomes a change on the short or full path.
- **A `wm-fix` skill runs the tiny path.** `wm-propose` asks first which path fits (tiny, short or full) and hands tiny work to `wm-fix`.
- **In an atlas, the planner may edit any code repo.** The session started in the atlas stays the one place work is done from, for changes and tiny fixes alike, across every code repo. The hooks no longer limit the planner to the repo of the item being built. A tiny fix across repos gets a branch of the same name and a pull request in each repo it touches. Implementers keep the one-repo limit, and nobody edits a spec by hand.
- **Specs stay functional.** This becomes a rule for every project:
  - `wm instructions` at the specs step and the `wm-propose` skill say that requirements describe what the system does, and that files, internals and mechanisms go in the design.
  - Waymark's charter gets the same rule for its specs step.
  - Waymark's `building` and `commits` specs are rewritten to fit.
- **The charter and docs** describe three paths: tiny, short and full. The goal "The human approves each change twice" now covers the tiny path's approval in the session and at the merge.

## Non-goals

- Recording tiny work anywhere in the record, such as a log.
- A size limit for the tiny path. The test is whether a requirement changes, not how many lines do.
- Checking from `wm` whether a commit should have been a change.
- Rewriting the `setup`, `atlas`, `review`, `archiving` or `agent-results` specs. They describe commands and files users see, which is this tool's behavior.
- Letting acceptance survive an added item, and moving the charter into config. These are the milestone's remaining changes.

## Impact

- New spec `paths`: the tiny path, and work done outside a change.
- Spec `building`:
  - "Delegation tag" and "Delegation tag accepted with the item" are modified to drop the item review level that no longer exists;
  - "Planner edits in an atlas" is modified: the planner may edit any code repo.
- Spec `commits`: "Commit messages checked in agent commands" is modified to describe which commits are checked, not how the message is parsed.
- **Behavior change for every user, for the changelog:**
  - a new `wm-fix` skill, written by `wm init` and `wm update`;
  - in an atlas, the planner may edit any code repo;
  - `wm instructions` at the specs step asks for functional requirements.
- Code: `hooks/decide.py` (the atlas edit rule), `services/instructions.py` (the specs guidance), `assets/` (the new skill), and the adapters' skill count.
- Assets: the new `wm-fix` skill, plus `wm-propose`, `wm-explore` and `wm-onboard`.
- Docs: concepts, getting started, the multi-repo guide, the smoke test, the README and the charter.

## Outcome

Work that adds, changes or removes no requirement now takes the tiny path: no change folder, the human's yes in the session, a conventional commit and a pull request, run by the new wm-fix skill; wm-propose asks which path fits (tiny, short or full) and wm-explore offers the tiny path. In an atlas the planner may edit any code repo from the atlas session, while implementers keep the one-repo limit and specs stay protected. wm instructions and wm-propose ask for functional requirements, Waymark's charter has the same rule, and the building and commits specs were rewritten to fit.

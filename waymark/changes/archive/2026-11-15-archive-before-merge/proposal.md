# Archive before merge

- **Owner:** Noah Roberts
- **Path:** short
- **Review:** self

## Why

A change is archived after its code is merged, so every change takes two pull requests: one for the code, and one for the archive. The last two changes on this milestone each needed a second branch, push, pull request and merge just to move a folder and merge the deltas into the specs.

Nothing in `wm` needs the merge first. Only the guidance says so: the `wm-archive` and `wm-apply` skills, `wm instructions` at the archive step, and the "not archived" warning in `wm check`. One thing in the way is real, though: `wm pr` describes only active changes, so it can't describe a change that is already archived on its branch.

## What changes

- **The archive goes on the change's branch, before the pull request.** Once every item is built and the change is reviewed, the planner archives it on its branch, when the human says so. The code, the merged specs and the archived change then go into one pull request, and the merge is the last step.
- **`wm pr` describes an archived change.** For a change archived on the current branch, it gives the same title, description and items as before, adds the outcome, and links to the archived proposal.
- **The guidance moves the archive before the pull request.** That covers `wm instructions` at the archive step, `wm check`'s "not archived" warning, the `wm-archive`, `wm-apply` and `wm-pr` skills, the docs and the smoke test.
- **If the pull request needs more work after the archive,** the archive commit is reverted, the work is done, and the change is archived again. The skills say so.

## Non-goals

- Checking in `wm` that a change's branch is merged, or reading anything from the git host.
- Archiving automatically when the last review passes. The human still decides when.
- The tiny path, and moving the charter into config. They are later changes on the milestone.

## Impact

- New spec `archiving`: archiving before the pull request, and a pull request described from an archived change.
- **Behavior change for every user, for the changelog:** a change is archived on its branch before its pull request, and `wm pr` works on an archived change.
- **Code:** `services/pr.py` and `services/common.py` (finding an archived change), `services/instructions.py` and `services/check.py` (the wording).
- Assets: the `wm-archive`, `wm-apply` and `wm-pr` skills.
- Docs: concepts, getting started and the smoke test, with `docs/cli.md` regenerated if the help text changes.

## Outcome

wm pr now describes an archived change: the latest archived change of a name, with its outcome and a link to the archived proposal, also with --repo in an atlas. wm instructions, the wm check warning, the wm-archive, wm-apply and wm-pr skills and the docs now put the archive on the change's branch, before its pull request; if the pull request needs more work, the archive commit is reverted and the change archived again. This change was the first archived on its own branch before its pull request.

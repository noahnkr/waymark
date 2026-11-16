# Merge milestone files

- Owner: Noah Roberts

## Why

A milestone is two files, `goal.md` and `roadmap.md`. They are always read together: the goal says why and when the milestone is done, and the roadmap lists the changes that get it there. Two files mean two templates, two links to keep straight, and a roadmap with its own title that repeats the goal's. One file reads in one place on GitHub.

This is the fourth change on the `record-format-and-skills` milestone.

## What changes

- **One file:** a milestone is a folder holding `milestone.md`, with its title, then `## Goal`, `## Done when`, `## Non-goals` and `## Roadmap`, in that order.
- **`wm new milestone`** writes `milestone.md` from one template.
- **Archiving a change** ticks its line in the `## Roadmap` section of `milestone.md`, and only list lines in that section are roadmap entries.
- **`wm check`** reports a `goal.md` or `roadmap.md` in a milestone folder, active or archived.
- **This repository's two milestones,** `record-format-and-skills` and the archived `lighter-workflow`, are merged by hand without changing their wording, and the links to their files are rewritten to `milestone.md`.
- **Skills and docs** show the one file.

## Non-goals

- A command or `wm check --fix` step that merges the two files: the human chose to merge this repository's milestones by hand, once.
- Rewriting links when `wm` moves a single file. The roadmap listed it for this change, but with the merge done by hand nothing moves a single file; archiving and closing already rewrite links when they move a folder.
- Checklists per drafting step: `add-step-guidance`.

## Impact

- Specs: `authored-formats` (modified)
- User-visible:
  - a milestone is one `milestone.md` instead of `goal.md` and `roadmap.md`;
  - `wm new milestone` writes `milestone.md`;
  - `wm check` reports a `goal.md` or `roadmap.md` in a milestone folder;
  - the record's two milestones change files, and links to them change.
- Code: `record/` (milestones, record, templates), `services/` (setup, lifecycle), `views/`
- Assets and docs: `wm-explore` and `wm-archive`, which describe a milestone's goal and roadmap; concepts and the changelog.

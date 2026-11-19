# Normalize finding places

- **Owner:** Noah Roberts
- **Path:** short

## Why

`wm review` and `wm verdict` write a finding's place exactly as it is given. A reviewer that names files by their absolute path puts the path of its machine into the record: four findings of link-milestone-changes read `C:\Users\<name>\project-workspace\waymark\src\...`. Such a place means nothing on another machine or on GitHub, it doesn't match the repo-relative places every other finding uses, and it publishes a person's home folder with the record.

## What changes

- A finding's place that starts with an absolute path inside the project is written relative to the project's top folder, with forward slashes, keeping what follows the path, such as `:12` or `: _spec_lines`. A relative path given with backslashes is written with forward slashes.
- In an atlas, a place inside a code repo registered on this machine is written as `<repo>/<path>`, such as `api/src/limit.py:12`.
- Any other absolute path is refused before anything is written, with the reason and the form to use.
- A place that isn't a path, such as a section of a doc, is written as given.
- The four findings of link-milestone-changes that hold an absolute path are rewritten relative to the project, as a one-off repair of an archived record.

## Non-goals

- No change to how links between docs and records are written: they are already relative, and resolve both in a clone and on GitHub.
- No rewriting of git history; the old text stays in the commits that wrote it.
- No check that a relative place names a file that exists.

## Impact

- **Specs:** `records` (added)
- **User-visible:**
  - `wm review` and `wm verdict` write a finding's absolute path as a path relative to the project, or `<repo>/<path>` in an atlas, and refuse any other absolute path
  - four archived findings of link-milestone-changes no longer show a home folder
- **Code:** `services/lifecycle.py` (the findings `wm review` and `wm verdict` take), `record/records.py`, the tests, `docs/record.md`, the CHANGELOG, and the archived `tasks.md` of link-milestone-changes

## Outcome

- **Built:** wm review and wm verdict write an absolute path in a finding's place relative to the project, with forward slashes and .. resolved, or as <repo>/<path> for a registered atlas code repo, and refuse any other absolute path. A relative path written with backslashes gets forward slashes, and prose places are kept as given. The four archived findings of link-milestone-changes no longer hold a home folder, and docs/record.md and the CHANGELOG describe it.
- **Differs:** The self-review found and fixed a prose place losing its backslashes and .. not being resolved. The archived findings were repaired by hand, since the hook refuses an agent's edit to Log records. Left open: Git Bash style paths are refused on Windows, and item 1.2's Verify search can't come back empty, so the criterion was checked with the full path.

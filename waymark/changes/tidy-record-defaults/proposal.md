# Tidy record defaults

- **Owner:** Noah Roberts
- **Path:** short
- **Review:** self

## Why

Some of what `wm new` writes into a new record file differs from file to file, and some lines are missing:

- **Review line.** A task item always carries its Build line, but a proposal carries a `- **Review:**` line only when the planner adds one. A reader has to know the project's `default_review` to tell what level a change is reviewed at.
- **Exploration comment.** A new exploration has a comment under its Status line that explains how `wm` changes it. The other comments in the templates say what to write in a section, so the planner removes them as it fills the section in. This one has nothing to fill in, so it is left in every exploration.
- **Charter glossary.** `wm check --fix` makes plain labels bold everywhere except the charter. A glossary entry written `- Record: …` or `- **Record**: …` is reported, but `--fix` leaves it as it is.

## What changes

- `wm new change` always writes a `- **Review:**` line under the Owner line, holding the project's `default_review`. On the short path it writes `self` when the default is `independent`. `wm check` reports an active change with no Review line as an error.
- The level is read only from the proposal's Review line, and is no longer filled in from the project's default.
- The exploration template drops the comment under its Status line. The hook's refusal of a hand edit still names `--from` and `wm exploration drop`.
- `wm check --fix` makes a charter glossary entry bold, as `- **<term>:** <meaning>`, when its term can be read.
- `wm-propose` and the propose step's guidance say that the Review line is already there and that the planner sets its value, rather than adding it.

## Non-goals

- Taking the comments that tell the planner what to fill in out of the templates. The planner removes those as it fills each section in, and no record file on `main` still holds one.
- Rules or checks for template comments left in a file.
- Migrating or reporting archived changes without a Review line. The check holds only active changes, and there are none.
- Other labels in the charter. It reads no labels besides its glossary entries.

## Impact

- **Specs:**
  - `review` (modified)
  - `authored-formats` (modified)
  - `formatting` (modified)
- **User-visible:**
  - `wm new change` writes a `- **Review:**` line holding the project's default level.
  - `wm check` reports an active change without one as an error.
  - New explorations have no comment under their Status line.
  - `wm check --fix` makes charter glossary entries bold.
- **Code:** creating a change in `services/setup.py`, the proposal check in `record/artifacts/proposal.py` and `record/artifacts/changes.py`, the exploration template, the charter in `services/fix.py` and `record/writing/layout.py`, the propose guidance in `services/instructions.py`, the `wm-propose` skill, `docs/record.md` and the CHANGELOG.

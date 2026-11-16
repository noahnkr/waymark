# Record format and skills

## Goal

Make the record read well on GitHub and parse without guesswork, and make the skills that draft it give consistent results. The record follows one convention: what a human writes is a `Capital-Label:` line or sub-bullet, and what `wm` writes is a dated `(lowercase)` record of the shape `(kind) DATE [args] [by WHO]: text`. Each change's evidence sits in a `## Log` section at the end of its task list. The skills share one layout. Their checklists, writing rules and shared rules come from `wm instructions`, and `wm check` enforces the mechanical parts.

## Done when

- Every line `wm` writes is a dated record of one shape, written and read by one module. `Blocked:`, `Spec gap:`, `Note:`, `Accepted:`, `Synced:` and `Review override:` are records like `(blocked)` and `(accepted)`, and each change's records sit in the `## Log` section of its task list.
- The proposal's human-written lines (`Owner`, `Review`, `Path`) and the charter's glossary render as lists on GitHub.
- `wm check --fix` rewrites the record into its standard form, and `wm update` migrates an existing record to the new format. Archived changes are still read as they were written.
- The human-written formats are settled:
  - charter: goals and constraints numbered, step headings capitalized;
  - task items: criteria as a nested list, the build tag as a `Build:` sub-line;
  - deltas: OpenSpec's section headings and a renamed section;
  - design: a decided-by and status line per decision, and open questions that block acceptance;
  - proposal: structured Impact and Outcome;
  - exploration: a `Status:` line;
  - milestone: one file.
- `wm instructions` gives each drafting step a checklist next to its template, plus the rules every skill shares, and each template carries a good and a bad example.
- Every skill follows one layout: role, inputs, steps, quality bar, what to show the human, when to stop, rules.

## Non-goals

- Stable IDs for requirements. Requirements keep their names as keys.
- A line tracing each item to the scenarios it covers.
- Front matter, a separate evidence file, or hidden comment markers.
- A history section in specs; git already records where a spec came from.
- An evaluation suite for the skills.

## Roadmap

- [standardize-record-lines](../../changes/archive/2026-11-16-standardize-record-lines/proposal.md): one record shape `(kind) DATE [args] [by WHO]: text`, written and read by one module; `(blocked)`, `(gap)`, `(note)`, `(accepted)`, `(synced)` and `(override)` as records; a `## Log` section at the end of the task list replaces `## Review` and holds every change-level record; finding places in backticks; `wm check --fix` for the standard layout, including human-written layout but never wording; record format 2, migrated by `wm update`
- [tidy-authored-notes](../../changes/archive/2026-11-16-tidy-authored-notes/proposal.md): the layouts a migration can make mechanically, in record format 3: the proposal's human lines as a bullet list; a bullet glossary and capitalized step headings that may be left out; criteria as a nested list and `- Build: delegate`; `## ADDED Requirements` headings and a renamed section with `From:` and `To:`; an exploration `Status:` line
- [structure-authored-notes](../../changes/archive/2026-11-16-structure-authored-notes/proposal.md): the formats that add meaning, required for new work only (existing content is migrated where mechanical and otherwise left as it is): a structured Impact (Specs, User-visible, Code) checked against the deltas, and a structured Outcome; numbered goals and constraints; `Decided by:` and `Status:` on decisions, with a proposed decision or an open question refusing acceptance; a good and a bad example in each template
- [merge-milestone-files](../../changes/archive/2026-11-16-merge-milestone-files/proposal.md): `goal.md` and `roadmap.md` become one `milestone.md`; `wm` rewrites Markdown links when it moves a file
- [add-step-guidance](../../changes/archive/2026-11-16-add-step-guidance/proposal.md): `wm instructions` gives a checklist for each drafting step and one preamble of the rules every skill shares; `wm check` enforces what it can
- sharpen-drafting-skills: one layout for every skill; rules for writing requirements and sizing items; a question step and a cross-artifact consistency check in `wm-propose`; fixed summaries for the human; a kickoff interview script; deeper exploration; a severity rubric for the reviewer and stopping rules for the implementer

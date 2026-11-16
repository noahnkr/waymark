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

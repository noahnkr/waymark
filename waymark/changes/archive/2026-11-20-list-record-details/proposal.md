# List record details

- **Owner:** Noah Roberts
- **Review:** independent

## Why

Every record is one line. When a note, a blocker, a review summary or a revision has several points, they get joined with semicolons into one long line, which is hard to read in a pull request. The `restyle-record` Log has a review summary that runs to six clauses. An archive's Outcome has the same problem: `--built` and `--differs` each take one paragraph. Findings already sit under their review as sub-bullets, so the record has a list form. It just isn't open to anything else.

## What changes

- **Details under a record.** `wm note`, `wm block`, `wm gap`, `wm resolve`, `wm review --self`, `wm verdict` and `wm revise` take a repeatable `--detail "<text>"`. Each detail is written as a sub-bullet under the record, `  - <text>`, in the order given. The record's own text stays a required one-line summary.
- **Under a review**, findings keep their `[<severity>] `<place>`: <text>` form, and a sub-bullet without a severity in brackets is a detail.
- **Agents.** An implementer's or reviewer's message may hold `DETAIL: <text>` lines anywhere before its two ending lines, the way `FINDING:` lines already work. Each becomes a detail under the record written from the ending.
- **Outcome.** `wm archive` takes `--built` and `--differs` more than once. A value given once is written inline, as today. Several values are written as nested bullets under a bare `- **Built:**` or `- **Differs:**`.
- **Views.** `wm show` (text and JSON), the implement pack's notes from earlier work, the review pack's earlier reviews and `wm pr` show each record's details under it.
- The skills, the agent definitions and the docs show how to give details.

## Non-goals

- Splitting a record's text on newlines or semicolons.
- Details on `(accepted)`, `(synced)`, `(ticked)`, `(archived)`, `(reopened)` or `(override)`, which carry no list.
- Rewriting existing records into lists.
- Details on a milestone's roadmap records.

## Impact

- **Specs:**
  - `records` (modified)
  - `review` (modified)
  - `agent-results` (modified)
  - `authored-formats` (modified)
- **User-visible:**
  - `--detail` on seven writing commands, and details as sub-bullets under their record.
  - `DETAIL:` lines in an implementer's or reviewer's ending.
  - `wm archive` takes `--built` and `--differs` more than once.
  - `wm show --json` gives each record its `details`, at a new schema version, and the context packs and `wm pr` show them.
- **Code:** the records module in `record/evidence/records.py`, the task list parser and Log writer in `record/artifacts/tasks.py` and `record/writing/edits.py`, the outcome in `record/artifacts/proposal.py` and `record/writing/edits.py`, the commands in `services/lifecycle.py` and `cli.py`, the agents' endings in `hooks/decide.py`, the views and packs in `views/` and `services/context.py`, `services/pr.py`, the skills and agent definitions, the docs and CHANGELOG.

## Outcome

- **Built:**
  - Seven writing commands take a repeatable --detail, written as sub-bullets under the record after any findings, and agents give DETAIL lines before their ending.
  - A detail can't have a finding's shape, bracketed or not, and the Log reader uses the same rule, so what wm writes reads back clean.
  - wm archive takes --built and --differs more than once, as nested bullets.
  - Details show in wm show, both packs and wm pr; the skills, agents, docs and CHANGELOG match.
- **Differs:**
  - The first review asked for changes to 2.2 (a broken code fence in docs/record.md, missing DETAIL lines in the endings); both were fixed, and 2.3 was added for a detail starting with a severity word reading as a finding.
  - The second review asked for changes to 2.3 again, so it went to the human, who chose one rule for a finding's shape; the deltas, design and 2.3 were revised, the change was accepted again, and the third review passed.
  - Item 2.3's new criterion was built on the already-ticked item, because wm reopen couldn't reopen it after the review was resolved.
  - Two suggestions are left open: the proposal's wording, and the docs not mentioning the refusal.

# List record details: design

## Context

- `record/artifacts/tasks.py` reads the Log line by line. A record line becomes a `ReviewRecord`. An indented sub-line is read as a finding: under a `(review)` or `(self-review)` it is added to that record's `findings`, a sub-line that isn't a finding is `malformed-finding`, and a finding under any other record is `misplaced-finding`.
- `record/writing/edits.py` `append_log(tasks, record, findings)` writes a record and its findings as `  - <finding>` sub-lines. `set_outcome` writes the Outcome from text that `services/lifecycle.py` `_outcome` builds from one `--built` and one `--differs`.
- `services/lifecycle.py` has one function per writing command. `cli.py` defines `--finding` as a repeatable option on `wm review` and `wm verdict`.
- `hooks/decide.py` reads an agent's ending with regular expressions: `_ITEM_LINE`, `_RESULT`, `_VERDICT`, and `_FINDING` for `FINDING:` lines anywhere in the message.
- `wm show` builds each record's payload in `views/payloads.py`, and `views/render.py` draws findings under a review. The packs in `services/context.py` and `wm pr` in `services/pr.py` each show records their own way.

## Approach

1. **Details in the model.** `ReviewRecord` gains `details: tuple[str, ...]`. The Log parser reads an indented sub-line under a record:
   - under a review, a line with a severity in brackets is a finding; a line that starts with a bare severity word, `critical`, `warning` or `suggestion`, is still reported as a finding without its brackets, as the `records` requirement "Findings name their place in backticks" asks; any other line is a detail;
   - under `(note)`, `(blocked)`, `(gap)`, `(resolved)` and `(revised)`, every line is a detail, and one with a severity in brackets is `malformed-detail`;
   - under any other kind, the line is `misplaced-detail`, naming the kinds that take details.

   `records.py` keeps the set of kinds that take details, `DETAILED`, and `check_detail(text)` refuses an empty detail, one over a line, or one that starts with a severity in brackets.
2. **Writing.** `append_log` takes `details` after `findings` and writes them as `  - <detail>` sub-lines after the findings. Every lifecycle writer of a `DETAILED` kind takes `details: Sequence[str] = ()`, checks each one, and passes them on. `cli.py` adds a repeatable `--detail` to those seven commands.
3. **Agents.** `hooks/decide.py` gains `_DETAIL` for `DETAIL:` lines, read like `_FINDING`. `_record` passes them to `block`, `report_gap` and `add_note`, and `_record_verdict` passes them to `verdict`. A `done` ending ignores them.
4. **Outcome.** `wm archive`'s `--built` and `--differs` become `action="append"`. `_outcome` writes one value inline, and several as `- **Built:**` followed by `  - <value>` lines. The proposal's outcome reader already takes nested bullets under a label, as the Impact's does.
5. **Views.** Each record payload in `wm show` gains `details`, and `show.change` goes to version 5. The text view draws details under their record, after findings. The implement pack's notes and the review pack's earlier reviews carry `details`, `DELEGATED_VERSION` goes to 4, and their text adds each detail under its note or review. `wm pr` writes each detail under its record, as it writes findings.
6. **Assets and docs.** The `wm-apply`, `wm-update` and `wm-archive` skills mention `--detail` and repeating `--built`. The implementer and reviewer definitions mention `DETAIL:` lines. `docs/record.md`, `docs/concepts.md` and the CHANGELOG describe details, and the CLI and JSON references are regenerated.

## Decisions

### Decision: Which commands take --detail
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `wm note`, `wm block`, `wm gap`, `wm resolve`, `wm review --self`, `wm verdict` and `wm revise`
  - the same without `wm revise`
  - every writing command
- **Choice:** the seven, `wm revise` included
- **Why:** these are the records whose text can hold several points; a revision often lists several edits, while an acceptance, a tick or an override carries none.

### Decision: How an agent gives details
- **Status:** decided
- **Decided by:** human
- **Options:**
  - `DETAIL: <text>` lines anywhere before the two ending lines
  - `- ` lines after the RESULT or VERDICT line
- **Choice:** `DETAIL:` lines before the ending
- **Why:** the ending lines must close the message, and `FINDING:` lines already work this way.

### Decision: Text and details
- **Status:** decided
- **Decided by:** human
- **Options:**
  - the record's text stays a required one-line summary, with details as sub-bullets under it
  - details replace the text when given
- **Choice:** the summary stays, with details under it
- **Why:** every record keeps one shape, and views that show one line per record still say something.

### Decision: Outcome with several values
- **Status:** decided
- **Decided by:** human
- **Options:**
  - one value inline, several as nested bullets under the label
  - always nested bullets
- **Choice:** one inline, several nested
- **Why:** an Outcome with one value per label keeps its current look, and archived Outcomes stay as they read today.

### Decision: Where details show
- **Status:** decided
- **Decided by:** human
- **Options:**
  - in `wm show`, the context packs and `wm pr`
  - in `wm show` only
- **Choice:** everywhere a record shows
- **Why:** a detail the reviewer or the implementer can't see in its pack, or a reader can't see in the pull request, is lost to them.

## Open questions

None.

## Risks and trade-offs

- Under a review, a sub-line meant as a finding but written with neither brackets nor a severity word is now read as a detail instead of being reported. One that starts with a severity word is still reported.
- The show and pack schemas change version again, so any script reading them has to follow.

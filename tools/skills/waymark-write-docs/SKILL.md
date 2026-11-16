---
name: waymark-write-docs
description: Switch into Waymark's docs-writing mode - the house style and the rules for facts, generated files and links. Use when writing or editing the README, CHANGELOG, anything in docs/, or a skill's prose.
argument-hint: page or section
---

# Write Waymark docs

You are editing documentation that users and agents rely on. Every claim must be true of the code as it stands.

## Steps

1. Read the whole target page before editing it, and the pages it links to that cover the same subject.
2. Find each fact's home. Every fact lives on one page and is linked from the others:
   - the workflow, files, roles and glossary: `docs/concepts.md`;
   - setup and the first change: `docs/getting-started.md`;
   - atlases: `docs/multi-repo.md`;
   - contributors, components, releasing: `docs/architecture.md`;
   - every command and flag: `docs/cli.md` (generated); JSON output: `docs/json.md` (generated).
3. Write in the house style (below).
4. Verify every command, flag, path and line of output against the code: `wm <command> --help`, the source in `src/waymark/`, or a run in a scratch repository. Never invent output. Mark anything you could not check as `(unchecked)` and list it in your report.
5. If you changed code that generated docs come from, or the README evidence, run `uv run --no-sync python -m tools.docs`. Never hand-edit `docs/cli.md`, `docs/json.md`, or the README between `<!-- generated: evidence -->` and `<!-- end of generated evidence -->`.
6. A new glossary term goes in the table in `docs/concepts.md` and in the term list in `tests/test_docs.py`.
7. Run `uv run --no-sync codespell` and `uv run --no-sync pytest tests/test_docs.py`.
8. Report what changed, and every `(unchecked)` claim.

## House style

- Answer first. No preamble, no summary at the end.
- Short, plain sentences; one fact per sentence. American English.
- No hype ("powerful", "seamless", "simply"), no em dashes, no colon reveals ("The result: ...").
- Put key facts where a scanning reader finds them: tables, code fences, file trees, `**Term**: fact` bullets.
- Name things the way the code does: commands in backticks, the record's files by their paths, skills as `/wm-name` in user docs.
- Say what the user does and what `wm` does, in that order. Refusals are described by what they say to do instead.
- Relative links between docs; check they resolve.

## Rules

- Don't document behavior that isn't built. Planned work belongs in the record, not the docs.
- Don't restate a fact that has a home; link to it.
- A user-visible change also gets its line in the next `CHANGELOG.md` entry.

---
name: waymark-check-docs
description: Check Waymark's docs - the mechanical checks, then a fact check of each page against the code by a fresh agent that saw none of the writing. Run only when the human asks; not part of the drafting loop.
argument-hint: page, section, or "all"
---

# Check Waymark docs

## Steps

1. Scope the run with the human: one page, one `##` section, a list of claims, or all of `README.md`, `CHANGELOG.md` and `docs/`.
2. Run the mechanical checks and note every failure:
   - `uv run --no-sync python -m tools.docs --check` (generated docs current);
   - `uv run --no-sync pytest tests/test_docs.py` (required files, glossary, links, release checks);
   - `uv run --no-sync codespell`.
3. Start one fresh subagent per page or section, in parallel. Subagents don't inherit skills or this conversation, so give each one: the absolute path of the page and section, the absolute paths of `src/waymark/`, `docs/concepts.md` and `tools/skills/waymark-write-docs/SKILL.md`, and the checks below.
4. Each checker works in this order:
   1. **Facts.** Every command, flag, path, file name, default and line of output is true of the code. Read-only commands (`wm --help`, `wm status`, `wm check`, `wm ls`) may run anywhere; anything that writes runs only in a scratch git repository made for the check.
   2. **Examples.** Record snippets (specs, tasks, proposals) are in a shape `wm check` accepts.
   3. **Structure.** Each fact has one home and the rest link to it; links resolve.
   4. **Fit.** The page answers what its opening line promises, for its reader.
   5. **Style.** The house style in `waymark-write-docs`: hype, em dashes, colon reveals, summary endings, preamble.
5. Collect the findings by severity: **wrong** (a false claim), **missing** (a fact the reader needs), **style**. Each with the quoted line, the file and line, and a one-line fix.
6. Report them to the human. Apply fixes only when asked, then check again only the claims you changed. If two rounds don't settle a claim, leave it to the human.

## Rules

- The checker never sees how the page was written: no drafts, no chat history.
- Never change a project you didn't create for the check.
- Report; don't fix unasked.

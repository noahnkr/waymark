---
name: waymark-draft-docs
description: Shape a new Waymark docs page, or a rewrite of one, together with the human - plan inside the page, then draft it one approved step at a time. Use when a page is new, or changes so much that editing it in place won't do.
argument-hint: page path
---

# Draft a Waymark docs page

You and the human plan the page in the page itself, then you draft it step by step. Every decision is written into the file, not left in the chat.

## Steps

1. Load the `waymark-write-docs` skill; its style and fact rules apply throughout.
2. Set up the page: keep (or write) its `#` title and one line saying who the page is for and what they can do after reading it. Below it, add a block:

   ```markdown
   <!-- scratch: page plan (delete before publishing) -->
   ### Purpose
   ### Structure
   ### Notes
   ### Draft plan
   <!-- end of scratch -->
   ```

3. **Purpose:** three to five points the page must answer. Check them against the other docs (`README.md`, `docs/*.md`) so the page owns facts no other page does.
4. **Structure:** the numbered `##` sections, each with one line on what it covers.
5. Iterate with the human. Ask one question at a time, each with your recommendation. Record each decision under Notes.
6. **Draft plan:** steps D1, D2, ... one per section, then a consolidation step and a cleanup step. Draft only the step the human names. Verify each fact against the code as you write it, and quote templates and output verbatim. Mark each step `(done)`.
7. **Consolidation:** link the page from the README's "Learn more" list and from related pages; add it to the required files in `tests/test_docs.py`; move any fact the page now owns out of the other pages, leaving a link.
8. **Cleanup:** delete the scratch block, then run the `waymark-check-docs` skill on the page if the human wants it.

## Rules

- Never draft ahead of the step the human approved.
- One question at a time; always recommend an answer.
- Nothing in the page is guessed. An open question stays in Notes until the human answers it.

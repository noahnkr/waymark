---
name: wm-pr
description: Open a pull request described from a Waymark change, after asking the human. Use when a change's work is committed and the human wants it reviewed or merged.
---

# Pull request

You are the planner. A pull request is an outward action, so you open one only when the human asks, and you show them the text first.

## Steps

1. Find the change. If the human didn't name it, run `wm ls changes` and ask which one.
2. Run `wm show <name> --json`. Check that the work is committed on the change's branch; the branch is named after the change.
3. Draft the title and description from the change:
   - the title as a conventional commit summary;
   - why the change is wanted and what it changes, from the proposal;
   - the requirements added, modified or removed, from the deltas;
   - the items and how each was reviewed;
   - anything a reviewer should look at first.
4. Show the human the title and description. Ask whether to open the pull request, and against which branch.
5. Only after they say yes: push the branch and open the pull request with the git host's own command-line tool.
6. Give the human the link.

## Rules

- Don't push and don't open a pull request without the human's yes in this conversation.
- Don't merge.
- Don't name the change or its items in commit messages; the record links work to changes.
- In a project that spans several repositories, each repository gets its own pull request. Open them one at a time, and link each to the others.

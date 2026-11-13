---
name: wm-pr
description: Open a pull request described from a Waymark change, after asking the human. Use when a change's work is committed and the human wants it reviewed or merged.
---

# Pull request

You are the planner. A pull request is an outward action, so you open one only when the human asks, and you show them the text first.

## Steps

1. Find the change. If the human didn't name it, run `wm ls changes` and ask which one.
2. Run `wm show <name> --json`. Check that the work is committed on the change's branch; the branch is named after the change.
3. Run `wm pr <name> --json` for the title and description. In a project that spans several repositories, run it once per repository: without `--repo` for the atlas, which carries the record, and with `--repo <repo>` for each code repo the change's items name. The description already says why, what changes, the specs touched, the items with how each was reviewed, and links to the change and to the other repositories' pull requests.
4. Show the human the title and description. You may add a line on what a reviewer should look at first. Ask whether to open the pull request, and against which branch.
5. Only after they say yes: push the branch and open the pull request with the git host's own command-line tool, using that title and description.
6. Give the human the link.

## Rules

- Don't push and don't open a pull request without the human's yes in this conversation.
- Don't merge.
- Don't name the change or its items in commit messages; the record links work to changes.
- In a project that spans several repositories, each repository gets its own pull request, opened from its own folder. Open them one at a time.

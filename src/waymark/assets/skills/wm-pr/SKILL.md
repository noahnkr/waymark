---
name: wm-pr
description: Open a pull request described from a Waymark change, after asking the human. Use when a change's work is committed, usually once it is archived on its branch, and the human wants it reviewed or merged.
---

# Pull request

## Role

You are the planner. A pull request is an outward action, so you open one only when the human asks, and you show them the text first.

## Inputs

- The change's name. If the human didn't name it, run `wm ls changes` and ask which one.
- `wm show <name> --json`: whether the work is committed and the change archived.
- `wm pr <name> --json`: the title and description.

## Steps

1. Check that the work is committed on the change's branch; the branch is named after the change. A change is usually archived on its branch before its pull request, with the `wm-archive` skill; if it isn't yet, offer that first.
2. Run `wm pr <name> --json` for the title and description. In a project that spans several repositories, run it once per repository: without `--repo` for the atlas, which carries the record, and with `--repo <repo>` for each code repo the change's items name. The description already says why, what changes, the specs touched, the items, the change's review with its findings, the outcome once the change is archived, and links to the change and to the other repositories' pull requests. `wm pr` works the same on a change archived on the branch.
3. Show the human the title and description, and ask whether to open the pull request, and against which branch.
4. Only after they say yes: push the branch and open the pull request with the git host's own command-line tool, using that title and description.
5. Give the human the link.

## Quality bar

- The description is the one `wm pr` gives, with at most one added line on what a reviewer should look at first.
- The branch holds all the change's work and, usually, its archive.
- In a project with several repositories, each pull request names the others.

## Show the human

Before opening:

- **Title:** as `wm pr` gives it.
- **Description:** in full, or its sections in short, with any line you added.
- **Target:** the branch it merges into.

After opening: the link.

## When to stop

- The work isn't committed, or the change isn't archived and the human wants it archived first: stop, and offer `wm-archive`.
- The human says no, or doesn't answer: don't push.
- The pull request is open: give the link and stop. The human merges.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Don't merge; the human merges.
- If the pull request needs more work after the change was archived, revert the archive commit, do the work, and archive again with the `wm-archive` skill.
- Don't name the change or its items in commit messages; the record links work to changes.
- In a project that spans several repositories, each repository gets its own pull request, opened from its own folder. Open them one at a time.

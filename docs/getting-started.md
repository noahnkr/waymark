# Getting started

This guide takes you from nothing to your first change, made with Waymark on your
own code. It takes one sitting. The first change is the tutorial: there is no demo
project.

## 1. Install

You need git, Python 3.11 or newer, and [Claude Code](https://code.claude.com).
Install `wm` as a standalone tool. The package is called **`waymark-cli`**:

```
pipx install waymark-cli
# or
uv tool install waymark-cli
```

Check it: `wm --version`. The agent tool's hooks and the git hooks call `wm`
from PATH, so it must be on PATH in the shell Claude Code uses.

## 2. Set up your repository

In the repository you want to work on (it must be a git repository; run
`git init` first if it isn't one):

```
wm init
```

This writes:

- `waymark/`, the record: `config.toml` (the settings, including the `wm`
  version this project pins) and `charter.md` (a skeleton to fill in);
- the skills in `.agents/skills/`, with copies in `.claude/skills/`, the two
  agent definitions in `.claude/agents/`, and the hooks in
  `.claude/settings.json` (merged into any settings you already have);
- the git hooks in `.waymark/hooks/`, which check commit messages and run
  `wm check` on commits that touch the record. `wm init` points this clone's git
  at them. If the repository already uses a hook manager, nothing is installed
  and `wm` prints the two lines to add to it.

Commit all of it, so anyone who clones the repository gets the same setup. Then
run `wm doctor` to check that everything is in place; it changes nothing.

Optional: `wm ci` adds a GitHub Actions workflow that installs the pinned `wm`
and runs `wm check` on every push and pull request.

> Each clone points git at the hooks itself (`core.hooksPath` is a per-clone
> setting). After cloning a project, run `wm git-hooks`; `wm doctor` and
> `wm status` warn when a clone hasn't.

## 3. Write the charter: the `wm-kickoff` skill

Start Claude Code in the repository and run the **`/wm-kickoff`** skill. It
interviews you about what the project is for (its vision, goals, non-goals,
constraints and glossary), looks at the repository to fill in the facts every
agent must know, and drafts `waymark/charter.md` and the settings. You edit and
approve the result. Nothing in the charter is taken from a guess.

## 4. Your first change: the `wm-onboard` skill

At the end of the kickoff, accept its offer of **`/wm-onboard`** (or run it
yourself). It takes one real, small change on your own code through every step,
and explains each one as it happens:

1. **Propose.** The agent drafts a proposal: why, what changes, non-goals,
   impact. A small change takes the short path: proposal and tasks, no design.
2. **Specs.** It writes the change's deltas against the living specs. On an
   existing codebase, this is where the first spec for that area is born.
3. **Tasks.** It writes the task list: each item with criteria, how to verify
   it, and a review level.
4. **Accept.** You read the change and run `wm accept <change>` yourself. Agents
   are blocked from running it.
5. **Apply.** The agent delegates each item to a fresh implementer agent, which
   builds it from the record alone, and records the result.
6. **Review.** Each item is checked at its level, and the check is written under
   the item.
7. **Archive.** Your second approval. Once you agree, the change is archived:
   its deltas merge into the specs and its outcome is written. `wm` refuses while
   any item is unbuilt or unreviewed; only you can archive past a missing review,
   with `wm archive <change> --override "<reason>"`.

## Every day after that

| You want to | Run |
|---|---|
| See where things stand | `wm status` |
| See what only you can settle | `wm inbox` |
| Start a change | the `/wm-propose` skill |
| Build an accepted change | the `/wm-apply` skill |
| Revise a change | the `/wm-update` skill |
| Think an idea through first | the `/wm-explore` skill |
| Open a pull request for a change | the `/wm-pr` skill |
| Archive a finished change | the `/wm-archive` skill |
| Check the record's health | `wm check` |

When you come back after a break, in a fresh session or on another machine,
`wm status` and `wm instructions` give the next step from the files alone.

## Upgrading

Each project pins one exact `wm` version in `waymark/config.toml`. With another
version installed, reading works and writing is refused, with the command that
installs the pinned one. To upgrade a project: change the pin, install that
version, run `wm update`, review what it changed, and commit.

## Next

- [Concepts and glossary](concepts.md): what every file and rule is for.
- [Multi-repo guide](multi-repo.md): when your project spans several repositories.
- [CLI reference](cli.md): every command.

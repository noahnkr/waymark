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

Check it: `wm --version`. The agent tool's hooks call `wm` from PATH, so it
must be on PATH in the shell Claude Code uses.

## 2. Set up your repository

In the repository you want to work on (it must be a git repository; run
`git init` first if it isn't one):

```
wm init
```

On a terminal, `wm init` opens with a welcome screen, then asks three questions,
one screen at a time:

| Question | Default |
|---|---|
| Is this repository a project or an atlas? For an atlas, its name. | a project |
| Which agent tools should `wm` set up? | the tools it finds here, or all of them |
| Add the CI workflow? | yes |

Use the arrow keys to move, Space to select a tool, and Enter to answer. Esc or
Ctrl+C cancels: `wm init` says `Setup canceled. Nothing was written.` and
writes nothing. Where the terminal can't read single keys, the same questions
come as numbered choices you type at a line.

`wm init --yes` asks nothing, and so do `--atlas <name>` and `--tool <name>`:
`wm init` then sets up a project (or the named atlas) with every agent tool, or
the ones you name, and no CI workflow. It also asks nothing when its input or
output isn't a terminal, as when an agent runs it.

This writes:

- `waymark/`, the record: `config.toml` (the settings, including the `wm`
  version this project pins) and `charter.md` (a skeleton to fill in);
- the skills in `.agents/skills/`, with copies in `.claude/skills/`, the two
  agent definitions in `.claude/agents/`, and the hooks in
  `.claude/settings.json` (merged into any settings you already have);
- a block in `.gitignore` that keeps the agent tool files out of git. They
  belong to each machine, not to the project;
- `.github/workflows/waymark.yml`, when you answered yes to the CI workflow.

`wm init` installs no git hooks and changes no git setting.

Commit `waymark/` and `.gitignore`, and the workflow if `wm init` added it.
They are the only files `wm init` wrote that `git status` shows. Then run `wm doctor` to check that everything is in place; it
changes nothing.

The block sits between two marker lines. `wm` rewrites what is between them, and
leaves the rest of `.gitignore` alone. With Claude Code, the block lists:

| Pattern | What it ignores |
|---|---|
| `/.agents/skills/wm-*/` | the skills `wm` writes |
| `/.claude/skills/wm-*/` | their copies for Claude Code |
| `/.claude/agents/wm-*.md` | the agent definitions |
| `/.claude/settings.json` | Claude Code's settings, with the hooks |

Your own skills and agents, `CLAUDE.md` and `AGENTS.md` are not in the block.
Commit or ignore them as you choose.

The CI workflow installs the pinned `wm` and runs `wm check` on every push and
pull request on GitHub Actions. To add it later, run `wm ci`. Nothing runs `wm check`
when you commit; CI is where it runs.

Commit messages are checked in Claude Code, by its command hook. Commits you
make by hand are not checked. See [the gates](concepts.md#the-gates).

### After cloning a project

Install the `wm` version the project pins, then run `wm init` in the clone. On
a terminal it shows the welcome screen and asks nothing. It finds the record
and sets up this machine: it writes the agent tool files and
adds the `.gitignore` block if it is missing. It doesn't change anything in
`waymark/`. Run it again and it says the machine is already set up.

`wm init` is refused in a clone when the installed `wm` isn't the pinned
version; the message gives the command that installs it. It is also refused
when the record is in another format than the installed `wm` reads; the message
says to install the `wm` version that wrote it.

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
   impact (the specs it touches, what users will see change, and the code), and
   the change's review level when it isn't the project default. A
   small change takes the short path: proposal and tasks, no design. Work that
   changes no requirement needs no change at all: `/wm-propose` takes it on
   the [tiny path](concepts.md#paths).
2. **Specs.** It writes the change's deltas against the living specs. On an
   existing codebase, this is where the first spec for that area is born.
3. **Tasks.** It writes the task list: each item with criteria and how to
   verify it.
4. **Accept.** You read the change and run `wm accept <change>` yourself. Agents
   are blocked from running it. A design decision still marked `proposed`, or a
   question listed under its Open questions, has to be settled first.
5. **Apply.** The agent builds each item itself, from the record, and records
   the result. An item whose `- **Build:**` line says `delegate` goes to a fresh
   implementer agent instead (see [who builds an item](concepts.md#who-builds-an-item)).
   What `wm` writes about an item is a dated record under it, such as
   `2026-01-15 (blocked) by Sam Doe: <reason>` (see [records](concepts.md#records)).
6. **Review.** Once every item is built, the whole change is checked once at
   its level, and the review and its findings are written in the `## Log` at the
   end of the task list (see [review](concepts.md#review)).
7. **Archive.** Your second approval. Once you agree, the change is archived on
   its branch, before its pull request: its deltas merge into the specs and its
   outcome is written, what was built and how it differs from the proposal,
   with `wm archive <change> --built "…" --differs "…"`. `/wm-pr` then describes the pull request, outcome included. `wm` refuses while
   any item is unbuilt or the change is unreviewed; only you can archive past a
   missing review,
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
| Tidy the record's layout, never its wording | `wm check --fix` |

When you come back after a break, in a fresh session or on another machine,
`wm status` and `wm instructions` give the next step from the files alone.

## Upgrading

Each project pins one exact `wm` version in `waymark/config.toml`. With another
version installed, reading works and writing is refused, with the command that
installs the pinned one. To upgrade a project: change the pin, install that
version, and run `wm update`. When it changes the record, `.gitignore` or the CI
workflow, it names them and asks you to review and commit the changes. It never
asks you to commit the agent tool files. `wm update` and `wm init` also delete
any skill folder named `wm-*` that the installed `wm` doesn't ship, and list
each file as `removed:`. Folders with other names are left
alone, so don't name your own skills `wm-*`. `wm update` never changes the
record's format. A record in another format than the installed `wm` reads is
refused, its format named, and nothing changes.

If the agent tool files were ever committed, git keeps tracking them even with
the `.gitignore` block in place. `wm doctor` warns about them, and gives the
`git rm -r --cached` command that stops tracking them and keeps your copies. Run
it, then commit.

## Next

- [Concepts and glossary](concepts.md): what every file and rule is for.
- [The record](record.md): every note, its sections and lines, and its checks.
- [Skills and agents](skills.md): what each skill and agent does, reads and writes.
- [Multi-repo guide](multi-repo.md): when your project spans several repositories.
- [CLI reference](cli.md): every command.

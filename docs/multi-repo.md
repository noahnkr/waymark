# Multi-repo guide

When a project's code spans several repositories, say a backend and a frontend,
its record lives in a repository of its own: an **atlas**. One change, with one
proposal, one set of deltas and one task list, can cover both; each task item
names the repository it works in.

This guide sets up an atlas for a backend (`notes-api`) and a frontend
(`notes-web`), then runs one change that spans both.

## How the pieces find each other

- **The atlas names its code repos** in `waymark/config.toml`, each with an
  optional path hint relative to the atlas, such as `../notes-api`.
- **Each machine keeps a registry** of where its atlases and code repos are:
  `%APPDATA%\waymark\registry.toml` on Windows,
  `~/Library/Application Support/waymark/registry.toml` on macOS, and
  `~/.config/waymark/registry.toml` (or under `$XDG_CONFIG_HOME`) on Linux. Set
  `WAYMARK_REGISTRY` to keep it elsewhere. `wm atlas register` writes it.
- **When the registry has no entry,** a path hint that leads to the right
  repository is used, and `wm` prints a note with the command that registers it.
  Fresh clones side by side work with no setup.
- **A code repo needs no Waymark files.** It may carry a pointer file,
  `.waymark/atlas.toml` (written by `wm atlas point`), and the git hooks (written
  by `wm git-hooks`). With either a pointer or a registry entry, `wm` commands
  run inside the code repo act on its atlas.
- **`wm` never clones, pulls or pushes.** Keeping the repositories present and up
  to date is yours to do.

## 1. Create the atlas

Put the three repositories side by side:

```
work/
  notes-atlas/
  notes-api/
  notes-web/
```

Then, in the atlas:

```
cd notes-atlas
git init
wm init --atlas notes
```

This writes the record, the agent tool files and the git hooks into the atlas,
and registers the atlas on this machine. Skills, agents and hooks live only in
the atlas; the code repos never need them.

## 2. Name the code repos

Add them to `waymark/config.toml` (the `wm-kickoff` skill offers to do this):

```toml
[atlas.repos.api]
path = "../notes-api"

[atlas.repos.web]
path = "../notes-web"
```

Then record where they are on this machine, and check the setup:

```
wm atlas register
wm atlas doctor
```

`wm atlas register` registers every code repo whose hint leads to it. For one
somewhere else, name it and its folder: `wm atlas register web ~/src/notes-web`.
It also attaches the code repos to your Claude Code sessions in the atlas, by
listing their folders in `.claude/settings.local.json`, a per-machine file that
is kept out of git. `wm atlas doctor` checks the registry, each repo's folder and
branch, and the pins; it changes nothing.

Commit the atlas, then start Claude Code in it and run `/wm-kickoff`.

## 3. Optional: pointers and git hooks in the code repos

In each code repo you may run:

```
wm atlas point notes   # writes .waymark/atlas.toml: the atlas's name, a path hint, the pin
wm git-hooks           # adds the commit-message check, and points this clone at it
```

Commit what they write if the repo's other users should have it too. A repo you
don't own, such as a client's, can stay untouched: the atlas works without both.

## 4. A change that spans both repos

Sessions run in the atlas. The planner drafts the change there as usual; what
changes is that the work is split by repository:

- the proposal's Impact names the repos touched;
- a delta may say which repos a spec covers, with a `Repos: api, web` line;
- **every task item names its repo**:

```markdown
## 1. Sharing

- [ ] 1.1 Add the share endpoint
  - Criteria: POST /notes/{id}/share returns a link that opens the note read-only
  - Repo: api
- [ ] 1.2 Show a share button
  - Criteria: the button copies the link from the endpoint
  - Repo: web
```

`wm check` reports an error for an item without a `Repo:` line, or one naming a
repo the settings don't list, and the change can't be accepted until it is fixed.

**Branches.** The change's name is the branch name in the atlas and in every repo
its items name. The `wm-apply` skill creates the branches where they're missing.
`wm status` shows each repo's current branch under the change and warns when one
differs while the change is being built.

**Building.** The implementer's context pack gives its item's repo folder on
this machine. Claude Code's hooks hold each implementer's edits to that repo, and
refuse the planner's edits in any code repo. An item whose repo isn't on this
machine can't be delegated until it is registered.

**Commits and pull requests.** Code is committed in the code repos and the record
in the atlas. Each repository gets its own pull request; the `wm-pr` skill opens
them one at a time with text from `wm pr`:

```
wm pr add-sharing              # the atlas's pull request, with the record
wm pr add-sharing --repo api   # the backend's
wm pr add-sharing --repo web   # the frontend's
```

Each description links to the change and to the other repositories' pull
requests from the same branch.

**Archiving** comes after the code pull requests are merged. `wm` can't see a
merge on the git host (it never uses the network), so that call is yours.

## CI

Run `wm ci` in the atlas: its workflow runs `wm check` on the record. The code
repos' CI runs nothing from `wm` and needs no access to the atlas; their commit
messages are checked locally, by the git hooks.

## Another machine, or a teammate

Clone the atlas and the code repos. Side by side, as the hints expect, everything
works at once; run `wm atlas register` to record them anyway. In other places,
register each one with its folder. `wm atlas doctor` says what is missing.

## Reading another atlas's specs

A project can read the specs of another atlas without copying them in. Add it to
the settings, with an optional path hint:

```toml
[references.billing]
path = "../billing-atlas"
```

`wm ls specs --from billing` lists its specs, `wm show <spec> --from billing`
prints one, and the explore context pack carries an index of them. Nothing is
written to the other atlas, and its version pin doesn't matter for reading.

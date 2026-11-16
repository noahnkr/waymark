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
- **A code repo needs no Waymark files.** It may carry a pointer: a
  `waymark/config.toml` that names its atlas and holds no record (written by
  `wm atlas point`). With either a pointer or a registry entry, `wm` commands
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

This writes the record and the agent tool files into the atlas, adds the
`.gitignore` block that keeps the agent tool files out of git (see [Getting started](getting-started.md#2-set-up-your-repository)), and
registers the atlas on this machine. Skills, agents and hooks live only in the
atlas; the code repos never need them.

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

Commit the atlas's `waymark/` and `.gitignore`, then start Claude Code in it and
run `/wm-kickoff`.

## 3. Optional: a pointer in each code repo

In each code repo you may run:

```
wm atlas point notes
```

It writes `waymark/config.toml` in the code repo. The file is a pointer, not a
record: its only table is `[pointer]`, with the atlas's name, a path hint
relative to the code repo, and the pin.

```toml
# A pointer, not a record: this repository's record lives in the Waymark atlas
# named below. Written by wm atlas point.
[pointer]
atlas = "notes"
path = "../notes-atlas"
wm_version = "<the atlas's pin>"
```

Commit it if the repo's other users should have the pointer. `wm atlas point` is
refused in a repository whose `waymark/config.toml` is a record. `wm init` is
refused in a code repo with a pointer, and the message names the atlas to run it
in. A repo you don't own, such as a client's, can stay untouched: the atlas
works without a pointer.

**A pointer written by `wm` 0.1.1 or earlier** is `.waymark/atlas.toml`. `wm`
still reads it when the code repo has no `waymark/config.toml`, and `wm doctor`
warns about it. Run `wm atlas point notes` to move it: the new pointer is
written, and the old file is removed, with its folder when nothing else is in
it.

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

**Building.** An item's context pack gives its repo folder on this machine.
The session started in the atlas is where all work is done from, across every
code repo. Claude Code's hooks let the planner edit any code repo, for a change
or a tiny fix, and the record at any time. An implementer edits a code repo only
while an accepted change's item being built names it; an edit in any other code
repo is refused with the repos it may edit now. A tiny fix that touches several
code repos uses a branch of the same name and a pull request in each. An item
whose repo isn't on this machine can't be delegated until it is registered.

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

**Archiving** goes on the atlas's change branch, before the atlas's pull request,
once every item is built and the change is reviewed. The atlas's pull request
then carries the merged specs and the archived change. Merge the code pull
requests first, or together with it; `wm` can't see a merge on the git host (it
never uses the network), so that call is yours.

## CI

Run `wm ci` in the atlas: its workflow runs `wm check` on the record. The code
repos' CI runs nothing from `wm` and needs no access to the atlas. Commit
messages are checked by Claude Code's command hook in the atlas's sessions, with
the atlas's commit scopes, so the commits agents make in the code repos are
checked too (see [the gates](concepts.md#the-gates)).

## Another machine, or a teammate

Clone the atlas and the code repos, and install the `wm` version the atlas pins.
Then run `wm init` in the atlas. It sets up this machine: the agent tool files
and the `.gitignore` block. It doesn't change the record.

Side by side, as the hints expect, the code repos are found at once; run
`wm atlas register` to record them anyway. In other places, register each one
with its folder. `wm atlas doctor` says what is missing.

A code repo where `wm` 0.1.1 ran `wm git-hooks` still points git at hooks that
call `wm run-hook`, which is gone, so its commits fail. Clean it up as
[Getting started](getting-started.md#upgrading) describes.

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

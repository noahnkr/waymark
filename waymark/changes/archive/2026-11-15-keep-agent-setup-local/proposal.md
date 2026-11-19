# Keep agent setup local

- **Owner:** Noah Roberts

## Why

`wm init` writes two kinds of files: the record (`waymark/`), which a team shares, and each machine's setup. The setup is the skills in `.agents/skills/` and the agent tool's folders (`.claude/`), plus the git hooks in `.waymark/hooks/`. Today the docs say to commit all of it. That shares one agent tool's configuration with everyone, and agent tool folders end up mixed with project code in reviews.

Keeping the setup per machine doesn't work today. In a clone that already has a record, `wm init` refuses ("This repository already has a record"), so a fresh clone has no command that sets it up. `wm update` comes closest, but it also migrates the record and tells you to commit what it wrote. If a project ignores `.waymark/`, installing the git hooks fails, because `wm` runs `git add` on them.

Waymark's own repository now keeps this setup out of git, so this is the first thing to fix for 0.1.1.

## What changes

- **`wm init` in a clone that has a record sets up this machine** instead of refusing. It writes the agent tool files, installs the git hooks, and makes sure they are ignored. It doesn't touch the record. Like `wm update`, it needs the pinned `wm` version, and it refuses with a pointer to `wm update` when the record needs migrating.
- **`wm` keeps the files it writes for a machine out of git.** `wm init`, `wm update` and `wm git-hooks` add a marked block to the repository's `.gitignore`. In a project, the block lists the shared skills `wm` writes, each agent tool's files, and the git hooks. In a code repo with only the git hooks, it lists the hooks. Lines outside the block are left alone. The atlas pointer, `.waymark/atlas.toml`, stays committable.
- **The git hooks are no longer staged.** They are still written, made executable, and set as this clone's `core.hooksPath`. Messages stop saying to commit them.
- **`wm doctor` warns when files `wm` writes for a machine are tracked in git**, and gives the `git rm -r --cached` command that stops sharing them. That command is the upgrade path for 0.1.0 projects. Its message for missing or outdated agent files says to run `wm init`, and no longer says to commit.
- **`wm update` stops telling you to commit the agent tool files and hooks.** It still asks you to review and commit changes to the record.
- **Docs:** `docs/getting-started.md`, `docs/multi-repo.md` and `docs/smoke-test.md` say to commit `waymark/` and `.gitignore`, and that each clone runs `wm init`.

## Non-goals

- Changing what is in the agent tool files, or which agent tools are supported.
- Untracking files for the user. `wm` runs no `git rm`; `wm doctor` only says what to run.
- Managing agent tool files `wm` doesn't write, such as `CLAUDE.md`, `AGENTS.md` or other tools' folders. A project ignores those itself if it wants to.
- A setting to go back to committing the setup. A project that wants it can delete the block and commit the files; `wm` won't add the block back unless `wm init`, `wm update` or `wm git-hooks` runs again.

## Impact

- New spec: `setup` (setting up a machine, ignoring its files, the git hooks, and the doctor check).
- Behavior change for every user, for the changelog. After cloning, run `wm init`. Agent tool files and the git hooks are now per machine and ignored. In a 0.1.0 project, `wm update` adds the ignore block, and `wm doctor` lists the tracked files to untrack.
- **Code:** `services/setup.py`, `services/integration.py`, `services/githooks.py`, `services/doctor.py`, the adapter interface and the Claude Code adapter, and a new `.gitignore` writer in `record/`.
- Docs: getting started, the multi-repo guide, the smoke test, and the regenerated CLI reference if any help text changes.

## Outcome

wm init in a clone that already has a record now sets up that machine, and wm init, wm update and wm git-hooks keep wm's machine files out of git through one marked .gitignore block. The git hooks are no longer staged, and wm doctor reports any machine files still tracked in git, with the git rm -r --cached command that untracks them. Two additions beyond the proposal: wm init refuses --tool and --atlas when a record exists, and the wm git-hooks command moved into services/integration.py.

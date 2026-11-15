# Drop waymark folder

Owner: Noah Roberts
Accepted: 2026-11-15 by Noah Roberts (fingerprint: 8ba9f502868720b2)

## Why

`.waymark/` holds two things.

- **The git hooks, in `.waymark/hooks/`.** The folder existed so the hooks could be committed and every clone could point `core.hooksPath` at them. Since 0.1.1 they are written per machine and ignored, so the folder now holds only files that are kept out of git. The hooks check two things:
  - commit messages, which nothing in Waymark reads, since the changelog comes from archived changes;
  - `wm check` on commits that touch the record, which CI already runs on every push and pull request.
- **The atlas pointer, `.waymark/atlas.toml`, in an atlas's code repos.** It is one committed file in a folder of its own, next to `waymark/config.toml`, which is where Waymark's settings live everywhere else.

OpenSpec, a comparable tool, enforces commit messages with no git hooks at all. Its multi-repo pointer is a `store:` key in the code repo's own `openspec/config.yaml`. Doing the same lets every repository carry one Waymark folder, `waymark/`, and nothing else.

## What changes

- **No git hooks.** `wm init` and `wm update` stop writing hooks.
  - In a clone set up by 0.1.1, they unset `core.hooksPath` when it is `.waymark/hooks` and delete `.waymark/hooks/`.
  - `wm git-hooks` and `wm run-hook` are removed.
  - The ignore block no longer lists the hooks.
  - `wm doctor` and `wm status` stop checking whether a clone runs them.
- **Commit messages are checked by the agent's command hook.** In Claude Code, a `git commit` whose message isn't a conventional commit is refused before it runs, with the reason. The check uses the project's commit scopes, as the commit-msg hook did. Commits made by hand are no longer checked.
- **The atlas pointer moves into `waymark/config.toml`.**
  - A code repo that points at an atlas keeps a pointer-only `waymark/config.toml`, holding the atlas's name, an optional path hint and the pin, and no record.
  - `wm atlas point` writes it.
  - `wm` still reads `.waymark/atlas.toml`, and `wm doctor` suggests moving it.
  - `wm check`, `wm status` and the other commands run in such a repo act on its atlas, as they do through the old pointer today.
- **Docs and charter:** getting started, the multi-repo guide, concepts, the smoke test, the CLI reference, and the charter's constraint naming `.waymark/`.

## Non-goals

- Checking commit messages in CI, or pull request titles. Either can come later.
- Checking commit messages in agent tools without hooks.
- Changing how atlases and code repos are found through the registry and path hints, or adding a clone URL to the pointer.

## Impact

- Spec `setup`:
  - "Git hooks not staged" is removed;
  - "Machine setup in a clone", "Machine files ignored", "Tracked machine files reported" and "Setup messages" are modified to drop the hooks.
- New spec `commits`: commit messages checked in the agent's commands.
- New spec `atlas`: the pointer in the code repo's settings, and reading the old pointer.
- **Behavior change for every user, for the changelog:**
  - no local commit-message check for commits made by hand;
  - `wm git-hooks` and `wm run-hook` are gone;
  - a project using husky, lefthook or pre-commit has to drop its two `wm run-hook` lines;
  - pointers move into `waymark/config.toml`.
- Code:
  - removed: `record/githooks.py` and `services/githooks.py`, plus the hook templates, the `git-hooks` and `run-hook` commands, and the hooks checks in `services/doctor.py` and `views/`;
  - changed: `hooks/decide.py` (commands), `record/pointer.py`, `record/project.py`, `services/atlas.py`, `services/integration.py` and `services/setup.py`;
  - added: a migration step for 0.1.1 clones.
- Docs: getting started, the multi-repo guide, concepts, the smoke test, architecture and the regenerated CLI reference.

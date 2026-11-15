# Drop waymark folder: design

## Context

- **Git hooks.** The git hooks code lives in four places:
  - `record/githooks.py`: `HOOKS_DIR`, the scripts, `hook_manager`, `hooks_status` and `make_executable`.
  - `services/githooks.py`: `install`, plus the `wm run-hook` checks `check_commit_message` and `check_staged_record`.
  - The templates `record/templates/hook-commit-msg` and `hook-pre-commit`.
  - The CLI commands `git-hooks` and `run-hook`.

  These call them:
  - `services/integration.py`: `setup_machine`, `git_hooks` and `ignore_patterns`, through `HOOKS_IGNORED`.
  - `services/setup.py` and `services/doctor.py` (`_hooks_check`).
  - `views/payloads.py`: the status payload's `git_hooks` field, its schema in `views/schemas.py`, and a warning in `views/render.py`.
- **The commit message check.** `record/commits.py` `commit_problem(message, scopes)` checks a message, and stays as it is.
- **Commands.** `hooks/commands.py` splits shell commands with `shlex` into `Invocation`s, and `commits_or_pushes` finds `git commit`. `hooks/decide.py` `_command(event)` doesn't get the project today.
- **The pointer.**
  - `record/pointer.py` reads `.waymark/atlas.toml`, which holds `atlas`, `path` and `wm_version`.
  - `record/project.py` `find_project` looks upward for `waymark/config.toml`, then for the pointer file, then in the registry. Any `waymark/config.toml` found is taken as a record.
  - `record/config.py` `parse_config` reports a top-level `atlas` that isn't a table as a problem.
  - `services/atlas.py` writes the pointer (`wm atlas point`), and `services/doctor.py` reads it for the pointers check.
- **Migrations.** `services/migrations.py` migrates the record format. The 0.1.1 hooks are machine state, not record format, so they don't go through it.

## Approach

1. **A pointer-only settings file.**
   - `record/pointer.py` reads and renders a `waymark/config.toml` whose only table is `[pointer]`, holding `atlas`, an optional `path` and `wm_version`.
   - `POINTER_FILE` becomes `waymark/config.toml`, and `OLD_POINTER_FILE` is `.waymark/atlas.toml`.
   - `is_pointer(text)` says whether a settings file is a pointer: valid TOML with a `pointer` table.
   - `parse_pointer` takes either file. In the old file the keys are at the top level; in the new one they are under `[pointer]`.
2. **Finding the project.** `find_project` looks upward for `waymark/config.toml`:
   - when it's a pointer, it goes through the pointer as `_through_pointer` does today;
   - otherwise it's the record.

   If the upward search finds no `waymark/config.toml`, it looks for `.waymark/atlas.toml` before trying the registry. `Project` gains `old_pointer: bool`, so `wm doctor` can warn.
3. **`wm atlas point`.** It writes the new pointer and, in the same transaction, removes `.waymark/atlas.toml`. It then removes `.waymark/` if the folder is empty. It refuses in a repository whose `waymark/config.toml` is a record.
4. **Commit messages in the command hook.**
   - `commands.commit_messages(command) -> list[str | None]` gives each `git commit` invocation's message, or `None` when it can't be read:
     - every `-m` or `--message` value, joined with blank lines the way git joins them;
     - a value of the form `$(cat <<'EOF' … EOF)` (any delimiter, quoted or not, with or without `-`) is replaced by the here-document's body;
     - any other `$(`…`)` or `$VAR` makes the message unreadable;
     - with `-F` or `--file`, the path is returned instead, and `decide` reads the file through `record/files.py`.
   - `_command(project, event)` checks each readable message with `commit_problem(message, config.commit_scopes)`, for every role, after the existing rules. It refuses with `The commit was stopped: <problem>`.
5. **Removing the hooks.**
   - Delete:
     - `services/githooks.py`;
     - the two hook templates;
     - the `git-hooks` and `run-hook` commands, with their entries in `hooks/commands.py`'s reading-command list;
     - `HOOKS_IGNORED`;
     - the status payload's `git_hooks` field and its warning.
   - `record/githooks.py` shrinks to what the cleanup needs, renamed to `record/oldhooks.py`:
     - `HOOKS_DIR = ".waymark/hooks"`;
     - `remove_old_hooks(root) -> bool`, which unsets `core.hooksPath` only when it equals `.waymark/hooks`, then deletes that folder and `.waymark/` if it is empty.
   - `setup_machine` calls `remove_old_hooks`, and reports "Removed the git hooks wm 0.1.1 installed" when it did. `ignore_patterns` no longer lists the hooks.
   - `wm doctor`:
     - drops `_hooks_check`;
     - its "machine files in git" check also looks for `.waymark/hooks`;
     - a new "pointer" check warns about an old pointer.
   - The status JSON schema drops `git_hooks`. Its schema version goes up by one, and `docs/json.md` is regenerated.
6. **Docs and charter.**
   - `docs/getting-started.md`: no git hooks. Commits are checked in Claude Code, and `wm check` runs in CI.
   - `docs/multi-repo.md`: the pointer in `waymark/config.toml`, and no `wm git-hooks`.
   - `docs/concepts.md`: the gates and the "enforced by" lines.
   - The README's "What's enforced" table.
   - `docs/smoke-test.md`: drop the `wip` git-hook step and add a refused `git commit -m wip` from the planner.
   - `docs/cli.md`, regenerated.
   - The charter's constraint no longer names `.waymark/`. It is edited as part of the docs item.

## Decisions

### Decision: How a pointer is told from a record's settings
- Options: a top-level `atlas = "<name>"` string, where a record's `atlas` is a table; a `[pointer]` table; a separate file name in `waymark/`.
- Choice: a `[pointer]` table.
- Why: It says what the file is on sight, and a record's settings can never contain it by accident. Telling them apart by whether `atlas` is a string or a table would be easy to get wrong when editing by hand. A second file name in `waymark/` would bring back two spellings of the same thing.

### Decision: Where commit messages are checked
- Options: the agent's command hook; `wm check --commits` in CI; pull request titles in CI.
- Choice: the agent's command hook only, as the human chose.
- Why: Agents make nearly every commit in a Waymark project. The hook refuses a bad message before the commit exists, so no history needs rewriting. The CI checks stay possible later.

### Decision: What to do with messages the hook can't read
- Options: refuse; allow.
- Choice: allow.
- Why: Refusing an editor commit or a message built from a variable would block legitimate commands to enforce a convention. That would go against the charter's "guard rails, not security".

### Decision: Clean up 0.1.1 hooks in `setup_machine`, not as a record migration
- Options: a record format migration; a step in `setup_machine`, which `wm init` and `wm update` both run.
- Choice: `setup_machine`.
- Why: `core.hooksPath` and the hook files belong to each clone, not to the shared record. Every clone has to clean up its own, which `wm init` and `wm update` do.

## Risks and trade-offs

- **Commits made by hand are not checked.** A human can commit `wip`. Pull request review and squash-merge titles remain the human's check, as in OpenSpec. The changelog says so.
- **Projects calling `wm run-hook` from a hook manager break** until they remove the lines: the command no longer exists, and the hook fails with a clear "invalid choice". The changelog names the lines to remove.
- **Here-document parsing is heuristic.** It reads the common forms agents use. Anything else is allowed, not refused.
- **A code repo's `waymark/` folder now holds only a pointer.** A reader could take it for a record. The file's first line says it is a pointer, and `wm status` names the atlas.

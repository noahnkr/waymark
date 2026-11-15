# Tasks

## 1. The pointer in the code repo's settings

- [x] 1.1 Read a pointer-only `waymark/config.toml`, and still read the old pointer   `review: independent`
  - Criteria: `record/pointer.py` reads and renders a `waymark/config.toml` whose only table is `[pointer]` (`atlas`, optional `path`, `wm_version`), tells it from a record's settings with `is_pointer`, and still parses `.waymark/atlas.toml`; `find_project` goes through a pointer found as `waymark/config.toml`, falls back to `.waymark/atlas.toml` before the registry, and marks a project found through the old file; `wm check` and `wm status` run in a code repo with either pointer act on the atlas, and the pointer is never reported as a broken record
  - Verify: tests in `tests/record/test_atlas.py` and `tests/test_atlas_cli.py` for the scenarios "Commands act on the atlas", "Check in a code repo" and "Atlas set up with 0.1.1" (status part)
  - Note: `parse_pointer` and `render_pointer` take `old=True` for `.waymark/atlas.toml`. `wm atlas point` still writes the old file through `render_pointer(..., old=True)` and `OLD_POINTER_FILE`, so 1.2 switches it to `POINTER_FILE`; its refusal on `waymark/config.toml` must then use `is_pointer`, or re-pointing is refused.
  - Note: `record/atlas.py` gained `pointer_file(folder)`, and `read_pointer` reads either place (new first), so `wm atlas doctor`'s pointer check already reads both and names the file it read; 1.2 only needs its tests.
  - Note: not handled here: `wm init` in a code repo with the new pointer goes to `_set_up_clone` and treats the pointer as a record; `services/githooks.py` and `integration.git_hooks` do too, but they go in 3.1.
  - (review) 2026-11-15 pass: pointer.py reads and renders the [pointer]-only waymark/config.toml, has is_pointer and still parses .waymark/atlas.toml; find_project goes through the new pointer, falls back to the old one before the registry and sets old_pointer; tests show wm status and wm check in a code repo with either pointer act on the atlas with no broken-record report, and pytest, ruff and mypy pass.
- [x] 1.2 Write the new pointer with `wm atlas point`, and warn about the old one
  - Criteria: `wm atlas point <atlas>` writes the `[pointer]` settings in `waymark/config.toml`, removes `.waymark/atlas.toml` in the same transaction and `.waymark/` when it is then empty, and refuses where `waymark/config.toml` is a record; `wm doctor` warns when the project was found through the old pointer and gives the `wm atlas point <atlas>` command; `wm atlas doctor` reads pointers in either place
  - Verify: tests in `tests/services/test_atlas.py` and `tests/services/test_doctor.py` for "Point a code repo", "Move the pointer" and "Atlas set up with 0.1.1" (doctor part)
  - Note: `record/store.Transaction` gained `delete(relative)`, rolled back with the writes, so `wm atlas point` removes `.waymark/atlas.toml` in the same transaction; `.waymark/` is removed after the commit only when empty.
  - Note: `tests/services/test_githooks.py::test_git_hooks_in_a_code_repo_lists_only_the_hooks` now writes `.waymark/atlas.toml` by hand instead of calling `point`, since `integration.git_hooks` still takes a pointer `waymark/config.toml` for a record; 3.1 deletes that test.
  - Note: `wm doctor`'s new check is named "pointer" and appears only for a project found through the old pointer.
  - (self-review) 2026-11-15: wm atlas point writes the [pointer] waymark/config.toml, deletes .waymark/atlas.toml in the same transaction (new Transaction.delete saves the bytes and restores them on rollback) and removes an empty .waymark/; refuses over a record's settings; wm doctor warns about an old pointer with the wm atlas point command; wm atlas doctor reads both. Store, atlas and doctor tests (45) and mypy pass.
- [x] 1.3 Refuse `wm init` in a code repo that points at an atlas
  - Criteria: `wm init` (with or without `--atlas`/`--tool`) in a repository whose `waymark/config.toml` is a pointer, or that has only `.waymark/atlas.toml`, is refused before anything is written, naming the atlas and saying to run `wm init` in the atlas; a repository with a record behaves as before
  - Verify: tests in `tests/services/test_setup.py` for "Init in a code repo", with the new and the old pointer
  - (self-review) 2026-11-15: init_project refuses before any write when waymark/config.toml is a pointer or only .waymark/atlas.toml exists, with or without --atlas/--tool, naming the atlas and saying to run wm init there; a repo with a record goes through as before. Six new cases and the setup tests (43) pass.

## 2. Commit messages in the command hook

- [x] 2.1 Read the message of each `git commit` in a shell command
  - Criteria: `hooks/commands.commit_messages` gives, for each `git commit` invocation, the message from `-m`/`--message` (several joined with blank lines), the body of a `$(cat <<'EOF' … EOF)` here-document in any of its usual spellings, the path given with `-F`/`--file`, or nothing when the message can't be read (no message option, another command substitution, a variable)
  - Verify: tests in `tests/hooks/test_commands.py` for each form, including commands joined with `&&` and a Windows-style path
  - Note: `commit_messages` returns `list[CommitMessage | None]`, not `list[str | None]`: `CommitMessage.text` is a message from `-m`, `CommitMessage.file` a path from `-F` (Windows backslashes come back as `/`), so `decide` can tell them apart. `-F -` (stdin, e.g. `git commit -F - <<'EOF'`), `--fixup`/`--squash`/`-C`/`-c`/`-t`, and `-m` combined with `-F` give `None`.
  - (self-review) 2026-11-15: commit_messages reads -m/--message (joined with blank lines), here-document bodies, -F/--file paths (Windows paths with /) and gives None when unreadable; returns CommitMessage(text|file) so decide can tell a message from a path, a sound departure from the design's str. Tried the agent heredoc form, chained commands, two -m, an editor commit and a Windows -F path by hand; hook tests (160) and mypy pass.
- [x] 2.2 Refuse a `git commit` whose message isn't conventional   `review: independent`
  - Criteria: `decide` refuses a shell command with a `git commit` whose readable message fails `commit_problem` with the project's commit scopes, for every role, with "The commit was stopped: <problem>"; a message read from `-F` is read through `record/files.py`; unreadable messages and commands outside a Waymark project are allowed; the existing command rules keep their order and wording
  - Verify: tests in `tests/hooks/test_decide.py` for every scenario of the `commits` delta, and one through `wm hook claude-code PreToolUse` in `tests/adapters/test_claude_code.py`
  - (review) 2026-11-15 pass: decide refuses non-conventional readable git commit messages with "The commit was stopped: <problem>" using the project's scopes, reads -F files through RecordFiles, allows unreadable messages and non-Waymark folders, leaves the existing command rules in their order and wording, and tests cover every commits scenario plus a PreToolUse adapter test; 892 tests, ruff and mypy pass.

## 3. No git hooks

- [ ] 3.1 Remove the git hooks, and clean up the ones 0.1.1 installed   `review: independent`
  - Criteria: the `git-hooks` and `run-hook` commands, `services/githooks.py`, the hook templates and the status payload's `git_hooks` field and warning are gone, with the status schema's version raised; `ignore_patterns` no longer lists the hooks; `record/oldhooks.py` `remove_old_hooks` unsets `core.hooksPath` only when it is `.waymark/hooks` and deletes that folder (and `.waymark/` when empty); `setup_machine` calls it and says when it removed them; `wm doctor` has no git hooks check and its tracked-files check includes `.waymark/hooks`; `wm init` writes no hooks and changes no git setting
  - Verify: tests in `tests/services/test_setup.py`, `tests/services/test_doctor.py`, `tests/views/` and `tests/test_cli.py` for every scenario of the `setup` delta; the full suite passes with the removed tests deleted

## 4. Docs

- [ ] 4.1 Update the docs and the charter for no `.waymark/` folder   `review: none`
  - Criteria: `docs/getting-started.md`, `docs/multi-repo.md`, `docs/concepts.md`, `docs/architecture.md`, the README's "What's enforced" table and `docs/smoke-test.md` no longer mention git hooks or `.waymark/` except as what `wm` cleans up from 0.1.1; they say commit messages are checked in Claude Code's command hook and `wm check` runs in CI; the multi-repo guide shows the pointer in `waymark/config.toml`; the smoke test checks that a planner's `git commit -m wip` is refused; the charter's constraint no longer names `.waymark/`; `docs/cli.md` and `docs/json.md` are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `python -m tools.docs --check`, `pytest tests/test_docs.py` and `codespell` pass; `grep -r "\.waymark" docs README.md` shows only the 0.1.1 cleanup and the old pointer

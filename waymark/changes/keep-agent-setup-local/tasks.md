# Tasks

## 1. The ignore block

- [ ] 1.1 Write and update the marked `.gitignore` block in `record/ignore.py`   `review: independent`
  - Criteria: `merged(current, patterns)` adds the block at the end of a file without one, replaces an existing block in place, returns the text unchanged when the block is current, keeps every line outside the block byte for byte (including CRLF line endings and a missing final newline), and handles a missing file (`None`)
  - Verify: unit tests in `tests/record/test_ignore.py`, one per scenario of "Machine files ignored" that the function covers
- [ ] 1.2 Declare each adapter's ignore patterns, and work out the block for a repository
  - Criteria: `Adapter.ignored` defaults to empty; the Claude Code adapter lists `/.claude/skills/wm-*/`, `/.claude/agents/wm-*.md` and `/.claude/settings.json`; `integration.ignore_patterns(tools, record=True)` gives `/.agents/skills/wm-*/`, each tool's patterns, then `/.waymark/hooks/`, and with `record=False` only `/.waymark/hooks/`; every path `integration_files` renders matches a pattern
  - Verify: tests in `tests/adapters/test_claude_code.py` and `tests/services/test_setup.py`, including one that matches each rendered path against the patterns with `git check-ignore` in a temporary repository

## 2. Git hooks

- [ ] 2.1 Install the git hooks without staging them, and add the ignore block   `review: independent`
  - Criteria: `githooks.install` writes the hooks, makes them executable and sets `core.hooksPath`, stages nothing, and no longer says to commit them; `wm git-hooks` writes the hooks-only block in a repository without a record and the full block in one with a record; it works when `.waymark/` is already ignored; a repository with another hook manager is still left alone
  - Verify: tests in `tests/services/test_githooks.py` for the scenarios of "Git hooks not staged" and "Code repo with git hooks only", checking `git diff --cached --name-only` is empty

## 3. Setting up a machine

- [ ] 3.1 Add `integration.setup_machine`, and use it in `wm update`
  - Criteria: `setup_machine` writes the agent tool files, the per-machine files and the ignore block in one transaction, runs `keep_local`, and installs the hooks; `wm update` calls it after migrating; its last line asks to review and commit only when the record, `.gitignore` or the CI workflow changed, naming them, and otherwise says this machine's files were updated, without a commit line
  - Verify: tests in `tests/services/test_setup.py` for "Block already current", "Block out of date" and "Update changes only machine files"
- [ ] 3.2 Let `wm init` set up this machine in a clone that has a record   `review: independent`
  - Criteria: with no record, `wm init` creates it as before and also writes the ignore block; with a record, it sets up this machine through `setup_machine` and changes nothing under `waymark/`; run again it changes nothing and says so; it is refused with the install command on another pinned version, and refused with a pointer to `wm update` when the record format is older; the `init` help text says it also sets up a clone
  - Verify: tests in `tests/services/test_setup.py` and `tests/test_cli.py` for every scenario of "Machine setup in a clone" and "New project", including one that commits the record, clones the repository, runs `wm init` in the clone and checks `git status --porcelain` is empty and a `wip` commit is refused

## 4. Doctor

- [ ] 4.1 Report machine files tracked in git, and point setup messages at `wm init`
  - Criteria: a new `git.tracked(root, paths)` in `record/git.py` lists the tracked paths among those given; `wm doctor` has a "machine files in git" check that warns with the count, the first path and one `git rm -r --cached` command grouped by top folder, and passes when nothing is tracked; the "agent tool files" warning says to run `wm init` and doesn't say to commit
  - Verify: tests in `tests/services/test_doctor.py` and `tests/record/test_git.py` for the scenarios of "Tracked machine files reported" and "Agent files out of date"; the doctor's JSON schema still validates (`tests/views/`)

## 5. Docs

- [ ] 5.1 Update the user docs for per-machine setup   `review: none`
  - Criteria: `docs/getting-started.md` says to commit `waymark/` and `.gitignore` and to run `wm init` after cloning, and lists what is ignored; `docs/multi-repo.md` says the same for the atlas and for another machine; `docs/smoke-test.md` expects nothing staged after `wm init` and adds a step that clones the scratch repository again, runs `wm init` and checks `wm doctor` passes; `docs/cli.md` and the README evidence are regenerated; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and `codespell` pass; `wm init` and `wm doctor` output quoted in the docs matches a run in a scratch repository

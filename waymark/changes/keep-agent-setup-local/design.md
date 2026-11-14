# Keep agent setup local: design

## Context

- `services/setup.py` `init_project` creates the record, then calls `integration.stage` to stage the agent tool files and `githooks.install` for the hooks. It refuses when `waymark/config.toml` exists.
- `services/integration.py` `update` migrates the record, then:
  - restages the agent tool files and the per-machine files (`stage_local` and `keep_local`, which use the clone's `.git/info/exclude`);
  - refreshes the CI workflow if it exists;
  - reinstalls the hooks.

  It ends with "Review the changes and commit them."
- `services/githooks.py` `install` writes `.waymark/hooks/*`, then:
  - stages the hooks with `git.stage` and `git.stage_executable`, which fails when the paths are ignored;
  - sets `core.hooksPath`;
  - tells the user to commit the hooks.
- `services/doctor.py` `_tool_files` compares the files on disk with `integration.integration_files`, and says to "Run wm update, then review and commit".
- Adapters declare `files()`, `reads`, `local_files()` and `local_reads`. `files()` takes the current text of the files in `reads`, so file paths are only known by rendering.
- `tests/test_constraints.py` enforces two boundaries:
  - only `record/` and `assets/` touch files, so the `.gitignore` reading and writing goes in `record/`;
  - only `adapters/` names a tool.
- `RecordFiles` and `Transaction` (in `record/`) read and write files relative to a root, all or nothing, and keep existing line endings. `.gitignore` is written through them.

## Approach

1. **The ignore block**: new module `record/ignore.py`.
   - `BEGIN = "# Waymark: this machine's agent tool files and git hooks, written by wm"` and `END = "# end of Waymark"`.
   - `render(patterns) -> str` gives the block.
   - `merged(current: str | None, patterns) -> str` returns the file's text with the block added at the end, or replaced in place. Lines outside the block stay byte for byte. A file missing its final newline gets one before the block.
   - Everything is pure text in, text out, so it is easy to test.
2. **What goes in the block.**
   - The `Adapter` base gains `ignored: tuple[str, ...]`, defaulting to empty. For Claude Code that is `("/.claude/skills/wm-*/", "/.claude/agents/wm-*.md", "/.claude/settings.json")`.
   - `services/integration.py` gains `ignore_patterns(tools, record: bool) -> list[str]`:
     - with a record: `/.agents/skills/wm-*/`, then each tool's `ignored`, then `/.waymark/hooks/`;
     - without a record: just `/.waymark/hooks/`.
   - `stage_ignore(transaction, files, patterns) -> FileChange` stages `.gitignore` only when the block differs.
3. **Hooks.**
   - `githooks.install(root)` stops calling `git.stage` and `git.stage_executable`, and drops the "commit them" line.
   - It also stages the hooks-only block when the repository has no record. With a record, the caller writes the full block. `install` gains a `record: bool` argument so it knows which case applies.
   - `wm git-hooks` passes whether `waymark/config.toml` exists at the root. In a project, it writes the full block from the settings' `agent_tools`, so `wm git-hooks` and `wm init` never fight over the block.
4. **`setup_machine`**: new function in `integration`.

   ```python
   def setup_machine(record: Record) -> list[FileChange]
   ```

   It does two things:
   - stages, in one transaction, the agent tool files, the per-machine files and the ignore block, then commits the transaction and runs `keep_local`;
   - runs `githooks.install`.

   It returns what changed, plus the hook lines.
   - **`init_project`:** when the record exists, it opens the record (`open_record`, then `require_pinned`) and refuses if `config.record_format != RECORD_FORMAT`, pointing to `wm update`. Then it calls `setup_machine` and reports with "This machine is set up" or "Already set up". When the record is new, it keeps creating it as now, and adds the ignore block to the same transaction.
   - **`update`:** keeps the migration and the CI refresh, and calls `setup_machine`. Its last line names only the shared files it changed (the record, `.gitignore`, the CI workflow): "Review the changes to <paths> and commit them." When only machine files changed, it says "Updated this machine's files." with no commit line.
5. **Doctor.**
   - `_tool_files` says `Run "wm init" to set them up.`
   - A new check, "machine files in git", runs `git ls-files` for the paths `wm` writes for a machine, through a new `git.tracked(root, paths)` helper in `record/git.py`.
   - When any are tracked, it warns: `<n> file(s) wm writes for each machine are tracked in git, starting with <path>. Stop sharing them, keeping your copies: git rm -r --cached <paths>`. The paths are grouped to their top folders (`.agents/skills/wm-*`, `.claude/...`, `.waymark/hooks`), so the command stays short.
6. **Docs.**
   - `docs/getting-started.md`: commit `waymark/` and `.gitignore`; after cloning, run `wm init`.
   - `docs/multi-repo.md`: the same for the atlas and for another machine.
   - `docs/smoke-test.md`:
     - setup expects nothing staged after `wm init`;
     - a new step: clone the scratch repo again, run `wm init`, and `wm doctor` passes.
   - Regenerate `docs/cli.md` if the `wm init` help text changes. The help text is "Create the record, or set up this machine in a clone that has one".

## Decisions

### Decision: Where the ignore lines go
- Options: the committed `.gitignore`; the clone's `.git/info/exclude`, which `keep_local` already uses for per-machine files.
- Choice: the committed `.gitignore`.
- Why: The exclude file belongs to one clone. A teammate who clones and runs an agent tool before `wm init` would see `.claude/` as new files to commit. `.gitignore` travels with the repository, so every clone is protected from the start.

### Decision: How the paths to ignore are known
- Options: list the paths that `integration_files` renders; have each adapter declare glob patterns; ignore whole tool folders (`/.claude/`).
- Choice: each adapter declares patterns (`Adapter.ignored`).
- Why: Rendering gives dozens of single files, which would make a long block that changes with every new skill. Whole folders would also ignore files the project owns, such as its own skills in `.claude/skills/`. Patterns stay short and match only what `wm` writes. The one exception is `settings.json`, which `wm` merges into.

### Decision: One block for every case
- Options: separate blocks for agent files and for hooks; one block whose contents depend on whether the repository has a record.
- Choice: one block, worked out from the repository each time.
- Why: Whichever command runs last (`init`, `update` or `git-hooks`) writes the same block for the same repository, so they can't undo each other. There is one marker pair to find and replace.

### Decision: `wm init` on an existing record, rather than a new command
- Options: a new `wm setup`; tell users to run `wm update`; let `wm init` set up the machine when the record exists.
- Choice: `wm init`.
- Why: It is the command people already run first. `wm update` also migrates the record, which a fresh clone should never do by accident. A new command would mean one more thing to learn.

### Decision: Untracking is left to the user
- Options: `wm update` runs `git rm --cached` on tracked machine files; `wm doctor` reports them with the command.
- Choice: report only.
- Why: Untracking changes what the whole team shares. That is the user's decision, like every other commit. It also keeps `wm` to the local, careful writes in the charter's constraints.

## Risks and trade-offs

- **Hooks are no longer enforced for teammates who skip `wm init`.** Their clone has no agent tool hooks and no git hooks. Mitigation:
  - `wm status` and `wm doctor` already warn when the clone doesn't run the git hooks;
  - the docs make `wm init` the first step after cloning;
  - CI still runs `wm check`.
- **`.claude/settings.json` is ignored as a whole.** Settings a team kept there stop being shared for new clones. Already-tracked copies stay tracked until someone untracks them, so nothing breaks on upgrade. The proposal and changelog name this.
- **A project that wants the old behavior** can delete the block and commit the files. The block comes back the next time `init`, `update` or `git-hooks` runs, so the project has to keep removing it. No setting is offered in 0.1.1.
- **Hand edits inside the block are lost** when it is rewritten. The marker line says `wm` writes it.

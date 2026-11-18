# waymark

## Vision

Waymark is spec-driven development for coding agents, built on living specs: plain
markdown in the repository that says what the system does today. Every change starts
as an edit to those specs and is approved by a human before anything is built. Each
task is built from the written change, by the main session or, when tagged, by a fresh
agent that sees only the record. Each change is reviewed once, as a whole, and riskier
changes by a second agent that never saw the build. The command-line tool, `wm`
(package `waymark-cli`), keeps track of where it all stands.

It is for solo developers and small teams (roughly two to five) building real projects
with coding agents, on new or existing codebases, in one repository or several (an
atlas).

## Goals

1. Agents work only from what is written down; a missing fact is written into the record or becomes a spec gap, not a guess.
2. Every review is recorded with its change, and evidence is written only by `wm`.
3. Anyone can pick up the work from the files and git alone, in any session, on any machine.
4. The human approves each change twice: at accept and at archive. Tiny work, which changes no requirement, is approved with a yes in the session and at the merge.
5. Work takes the path its size needs: tiny work (no requirement changes) needs no change, small changes take the short path, big ones get a design, and risky ones an independent review.
6. Waymark is developed with Waymark: this record is the source of truth for its own work.

## Non-goals

- Handing an agent a goal and walking away.
- Throwaway scripts.
- Access control, approval chains, or security against someone set on getting around the guard rails.
- Calling a model, or any network access, from `wm`.

## Constraints

1. Python 3.11 or newer, standard library only at runtime; development tools are dev-only dependencies.
2. Deterministic and offline: `wm` never calls a model and never clones, pulls or pushes; it runs only local git commands.
3. Windows, macOS and Linux alike: portable paths, UTF-8 files, existing line endings kept, no symlinks.
4. No cache: every command reads the files fresh; views stay within about a second on a record with a few hundred changes and specs.
5. Careful writes: `wm` edits only the lines it owns, and a multi-file operation completes or leaves the record as it was. The one exception is `wm check --fix`, run when the human asks, which changes the layout of any file in the active record but never its wording.
6. Only code in `src/waymark/adapters/` may name an agent tool; only `record/` and `assets/` touch files (held by `tests/test_constraints.py`).
7. Agent tool folders and files (`.agents/`, `.claude/`, `CLAUDE.md`, `AGENTS.md`, `.codex/`, `.cursor/`) are per machine and never committed; each clone sets them up with `wm init`. The maintainer skills are committed in `tools/skills/` and installed into the tool folders with `python -m tools.install_skills`.

## Glossary

- **Record**: everything Waymark keeps in `waymark/`; the full glossary is in `docs/concepts.md`.
- **Atlas**: a separate repository holding the record for a project spread over several repositories.
- **Adapter**: the code that connects `wm` to one agent tool: renders its files, translates its hook events.
- **Asset**: a skill or agent definition shipped in `src/waymark/assets/`, tool-neutral.
- **Maintainer skill**: a skill in `tools/skills/` for working on Waymark itself (docs, releases); installed per machine for contributors, and not shipped to users.
- **Smoke test**: the manual run of one change through Claude Code before each release (`docs/smoke-test.md`).

## Context

- Layout: `src/waymark/` with `cli.py`, `record/`, `services/`, `views/`, `hooks/`, `adapters/`, `assets/`; tests in `tests/` mirror it; `tools/docs.py` (generated docs) and `tools/release.py` (release checks); user docs in `docs/`. `docs/architecture.md` describes the components.
- Setup: `uv sync`, then `uv tool install --editable . --force` so `wm` on PATH runs this checkout and matches the pin; then `wm init`, then `uv run --no-sync python -m tools.install_skills` for the maintainer skills.
- Checks, each via `uv run --no-sync`: `pytest`, `ruff format .`, `ruff check .`, `mypy`, `codespell`, `python -m tools.docs` (regenerates `docs/cli.md`, `docs/json.md` and the README evidence; a test fails when they are stale).
- CI (`.github/workflows/ci.yml`) runs tests on Windows, macOS and Linux with Python 3.11 and the newest, plus lint, format, types, spelling, the wheel build and `wm check`. Pushing a `v*` tag runs `release.yml`, which publishes to PyPI.
- Commits follow Conventional Commits in American English, scoped by component when one applies.
- Owner and maintainer: Noah Roberts.

## Rules

1. A change that alters what users see (commands, output, files written, the record format) says so under Impact, for the changelog.
2. Requirements describe what `wm` does as a user or an agent sees it: its commands, their output, and the record's files and formats. Modules, functions and other internals go in the design.
3. Every new rule gets a test named after it.
4. Docs that a change makes stale get their own item.
5. Run the checks the item touches, and the full checks (pytest, ruff, mypy, codespell, `tools.docs --check`) once before the pull request.
6. Never hand-edit generated docs; run `uv run --no-sync python -m tools.docs`.
7. Docs follow the `waymark-write-docs` skill.
8. Releases are cut with the `waymark-release` skill, never by hand.
9. A change with a User-visible line adds it to `CHANGELOG.md` under `## [Unreleased]`, in the item that updates its docs; the release turns that heading into the version's entry.

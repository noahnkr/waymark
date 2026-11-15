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

- Agents work only from what is written down; a missing fact is written into the record or becomes a spec gap, not a guess.
- Every review is recorded under its task, and evidence is written only by `wm`.
- Anyone can pick up the work from the files and git alone, in any session, on any machine.
- The human approves each change twice: at accept and at archive.
- Small changes stay light (the short path); big ones get a design, and risky ones an independent review.
- Waymark is developed with Waymark: this record is the source of truth for its own work.

## Non-goals

- Handing an agent a goal and walking away.
- Throwaway scripts.
- Access control, approval chains, or security against someone set on getting around the guard rails.
- Calling a model, or any network access, from `wm`.

## Constraints

- Python 3.11 or newer, standard library only at runtime; development tools are dev-only dependencies.
- Deterministic and offline: `wm` never calls a model and never clones, pulls or pushes; it runs only local git commands.
- Windows, macOS and Linux alike: portable paths, UTF-8 files, existing line endings kept, no symlinks.
- No cache: every command reads the files fresh; views stay within about a second on a record with a few hundred changes and specs.
- Careful writes: `wm` edits only the lines it owns, and a multi-file operation completes or leaves the record as it was.
- Only code in `src/waymark/adapters/` may name an agent tool; only `record/` and `assets/` touch files (held by `tests/test_constraints.py`).
- Agent tool setup (`.claude/`, `CLAUDE.md`, `AGENTS.md`, `.codex/`, `.cursor/`, the generated `.agents/skills/wm-*/`) is per machine and never committed; each clone sets it up with `wm init`. The maintainer skills in `.agents/skills/` are committed.

## Glossary

Record: everything Waymark keeps in `waymark/`; the full glossary is in `docs/concepts.md`.
Atlas: a separate repository holding the record for a project spread over several repositories.
Adapter: the code that connects `wm` to one agent tool: renders its files, translates its hook events.
Asset: a skill or agent definition shipped in `src/waymark/assets/`, tool-neutral.
Maintainer skill: a skill in `.agents/skills/` for working on Waymark itself (docs, releases); not shipped to users.
Smoke test: the manual run of one change through Claude Code before each release (`docs/smoke-test.md`).

## Context

- Layout: `src/waymark/` with `cli.py`, `record/`, `services/`, `views/`, `hooks/`, `adapters/`, `assets/`; tests in `tests/` mirror it; `tools/docs.py` (generated docs) and `tools/release.py` (release checks); user docs in `docs/`. `docs/architecture.md` describes the components.
- Setup: `uv sync`, then `uv tool install --editable . --force` so `wm` on PATH runs this checkout and matches the pin; then `wm init`.
- Checks, each via `uv run --no-sync`: `pytest`, `ruff format .`, `ruff check .`, `mypy`, `codespell`, `python -m tools.docs` (regenerates `docs/cli.md`, `docs/json.md` and the README evidence; a test fails when they are stale).
- CI (`.github/workflows/ci.yml`) runs tests on Windows, macOS and Linux with Python 3.11 and the newest, plus lint, format, types, spelling, the wheel build and `wm check`. Pushing a `v*` tag runs `release.yml`, which publishes to PyPI.
- Commits follow Conventional Commits in American English, scoped by component when one applies.
- Owner and maintainer: Noah Roberts.

## Rules

### explore

### propose

- A change that alters what users see (commands, output, files written, the record format) says so under Impact, for the changelog.

### specs

### design

### tasks

- Every new rule gets a test named after it.
- Docs that a change makes stale get their own item.

### apply

- Run the checks the item touches, and the full checks (pytest, ruff, mypy, codespell, `tools.docs --check`) once before the pull request.
- Never hand-edit generated docs; run `uv run --no-sync python -m tools.docs`.
- Docs follow the `waymark-write-docs` skill.

### review

### archive

- Releases are cut with the `waymark-release` skill, never by hand.

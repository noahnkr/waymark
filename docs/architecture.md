# Architecture notes

For contributors: how `wm` is put together, how hook decisions work, how to add an
adapter for another agent tool, and how to work on the code.

## Constraints

- **Python 3.11 or newer, standard library only at runtime.** Development tools
  are dev-only dependencies.
- **Deterministic, with no network access.** `wm` never calls a model and never
  clones, pulls or pushes. It runs only local git commands.
- **Windows, macOS and Linux alike.** Paths are handled portably, files are read
  and written as UTF-8, existing line endings are kept, and nothing depends on
  symlinks.
- **No cache.** Every command reads the files fresh; views stay within about a
  second on a record with a few hundred changes and specs (a test holds this).
- **Careful writes.** `wm` edits only the lines it owns, leaves everything else
  byte for byte, and a multi-file operation such as archive either completes or
  leaves the record as it was.

## Components

```
                          you                   agent tool (Claude Code)
                           |                  skills, subagents, hooks
                           v                              |
  +---------------------------- cli.py ------------------+---------------+
  |  thin: parses arguments, calls a service, prints     | wm hook <...> |
  +-------+-----------------------+-----------------------+-------+-------+
          v                       v                               v
  +--------------+   +----------------------------+   +--------------------+
  |   views/     |   |   services/                |   |   hooks/           |
  |  payloads,   |   |  setup, lifecycle, check,  |   |  neutral events,   |
  |  schemas,    |   |  instructions, context     |   |  decisions         |
  |  text + JSON |   |  packs, atlases, git hooks |   |                    |
  +------+-------+   +-------------+--------------+   +---------+----------+
         |                         |                            |
         v                         v                            v
  +-------------------------------------------------------------------------+
  |  record/   find the project; parse every artifact; derive state; merge   |
  |            deltas; fingerprints; the transactional writer; templates     |
  +-------------------------------------------------------------------------+
                    |
              files in waymark/, and git

  adapters/   one per agent tool: renders its files, translates its hook events
  assets/     the skills and agent definitions, tool-neutral package data
```

| Folder under `src/waymark/` | Holds |
|---|---|
| `record/` | The only code that reads or writes the record's files: parsers, state derivation, delta merging, the acceptance fingerprint, the transactional writer, templates, the registry, git queries. |
| `services/` | What the commands do, and every gate. A refused command raises `Refusal` with what is wrong and what to do next. |
| `views/` | Payloads, their JSON schemas, and the text and JSON renderers. One payload feeds both renderings. |
| `hooks/` | Tool-neutral hook decisions on six neutral events. |
| `adapters/` | One adapter per agent tool. Only code here may name a tool. |
| `assets/` | The skills and agent definitions, written once and tool-neutral. |
| `cli.py` | Parses arguments, calls a service, prints. |

Three tests in `tests/test_constraints.py` hold the boundaries: the standard
library only at runtime, no agent tool named outside `adapters/`, and no file
access outside `record/` and `assets/`.

## How hook decisions work

Claude Code runs `wm hook claude-code <Event>` with its JSON on standard input.

1. **The adapter translates** the payload into one of six neutral events:
   session start, delegate (starting a subagent), edit (before an edit), edited
   (after an edit), command (a shell command) and agent stop. It works out who
   is acting from the agent type: the implementer, the reviewer, or anyone else,
   who counts as the planner.
2. **The core decides** (`hooks/decide.py`): allow, refuse with a reason that
   says what to do instead, add context for the agent, or record evidence. For
   example, at an agent stop it reads the `ITEM:` and `RESULT:` or `VERDICT:`
   lines and writes the tick, blocker, spec gap, note or review record through the
   same lifecycle service the commands use.
3. **The adapter translates the decision back** into the tool's reply format.

The adapter holds no rules, so a decision is the same in every tool. A hook that
fails never blocks the agent: it reports the failure and steps aside. Outside a
Waymark project every event is allowed.

## Adding an adapter for another agent tool

An adapter is a subclass of `waymark.adapters.Adapter`:

- `name` and `title`, and `capabilities`: whether the tool has skills, isolated
  subagents and hooks. The workflow adapts to what is missing.
- `files(existing)`: the files Waymark owns in the tool's folders, with their
  full text. `reads` names project files the adapter merges into (their current
  text is passed in); merge, never overwrite what the project owns.
- `local_files(existing, folders)`: optional per-machine files, for attaching an
  atlas's code repo folders to sessions.
- `hook(event, payload, cwd, today)`: translate the tool's hook payload into a
  neutral `Event`, call `decide`, and translate the `Decision` back.

Register it in `adapters/__init__.py`. The skills in `.agents/skills/` are shared
by every tool; an adapter only adds its own copies and settings. No change to the
core or the skills is needed: a stub second adapter in the tests proves it.

## Working on the code

[uv](https://docs.astral.sh/uv/) manages the environment and the lockfile:

```
uv sync                                   # create .venv with the dev tools
uv run --no-sync pytest                   # tests
uv run --no-sync ruff format .            # format
uv run --no-sync ruff check .             # lint
uv run --no-sync mypy                     # strict type check (add --platform linux / darwin)
uv run --no-sync codespell                # spelling, American English
uv run --no-sync python -m tools.docs     # regenerate the CLI and JSON references and the README's evidence
```

CI runs the tests on Windows, macOS and Linux, each on Python 3.11 and the newest
release, plus lint, format, strict type and spelling checks, and builds the wheel.
A test fails when a generated doc is out of date.

| Dev tool | Why |
|---|---|
| uv | One tool for environments, the lockfile and every Python version CI tests |
| hatchling | Small, standard build backend that handles the `src/` layout and package data |
| pytest | The standard test runner; plain asserts and temporary-folder fixtures |
| ruff | Linter and formatter in one, so there is one style configuration |
| mypy | The reference type checker, in strict mode |
| codespell | Spelling check with a British-to-American dictionary |

**Tests.** Every rule has a test named after it. Test projects are built in
temporary folders while the tests run; nothing that looks like a sample project
is committed.

**Commits** follow [Conventional Commits](https://www.conventionalcommits.org/),
scoped by component (`record`, `services`, `views`, `hooks`, `adapter-claude`,
`cli`, `skills`, `docs`, `ci`, `build`), in American English.

## Releasing

The maintainer releases. Before each release, the [smoke-test checklist](smoke-test.md)
is run by hand, and its result goes into the changelog's entry. Then:

1. set the version in `src/waymark/__init__.py` and date the entry in `CHANGELOG.md`;
2. merge, and push a tag `v<version>` on `main`.

The release workflow checks that the tag, the version, the changelog entry and the
smoke-test record agree, runs the tests, builds, publishes to PyPI through trusted
publishing, and creates the GitHub release from the changelog entry.

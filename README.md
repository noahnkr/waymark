# Waymark

Waymark is spec-driven development for developers who want to stay in charge of
their project while agents write the code. Its model of living specs plus change
deltas follows [OpenSpec](https://github.com/Fission-AI/OpenSpec).

> **Status: pre-release.** This repository holds the project skeleton only. The
> `wm` command installs and runs, but it has no commands yet. Nothing is
> published on PyPI.

## Development

Waymark needs Python 3.11 or newer and uses only the standard library at
runtime. Development uses [uv](https://docs.astral.sh/uv/):

```
uv sync                  # create .venv with the dev tools
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy              # strict type check
uv run codespell         # spelling, American English
uv run wm --version      # run the command
```

CI runs the tests on Windows, macOS and Linux, each on Python 3.11 and the
newest Python release, plus the lint, format, strict type and spelling checks.

### Dev tools

| Tool | Why |
|---|---|
| uv | One tool for environments, the lockfile and every Python version CI tests |
| hatchling | Small, standard build backend that handles the `src/` layout and package data |
| pytest | The standard test runner; plain asserts and temporary-directory fixtures |
| ruff | Linter and formatter in one fast tool, so there is one style configuration |
| mypy | The reference type checker; `strict` mode keeps the code fully typed |
| codespell | Spelling check with a British-to-American dictionary, so the project stays in American English |

### Commits

Commits follow the [Conventional Commits](https://www.conventionalcommits.org/)
format, scoped by component, for example `feat(cli): ...`. Everything is written
in American English, commit messages and pull requests included.

## License

[MIT](LICENSE)

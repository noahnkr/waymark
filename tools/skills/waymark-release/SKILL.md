---
name: waymark-release
description: >-
  Release a new version of Waymark (waymark-cli) - audit what changed since the
  last tag, prepare the version, pin and changelog on a release branch, run the
  checks, wait for the human's smoke test, open the pull request, and tag only
  when the human says so. Use when the human asks to release, cut or ship a
  version, or to continue a release paused for the smoke test or the merge.
argument-hint: version (optional)
---

# Release Waymark

A release is cut from `main` by pushing a tag `v<version>`. `.github/workflows/release.yml` then checks the tag, version, changelog and smoke-test record (`tools/release.py`), runs the tests, builds, publishes to PyPI through trusted publishing, and creates the GitHub release from the changelog entry. This skill gets everything ready for that, and pushes the tag only on the human's word.

Work out where the release stands from git and GitHub each time you run, and take only the next step.

## 1. Audit

1. `git fetch origin --tags --prune`. `main` must be checked out, clean and equal to `origin/main`; otherwise say what differs and stop.
2. The last release is the newest `v*` tag (`git tag --sort=-v:refname`). If a `release-v*` branch or pull request already exists, resume from the step it reached.
3. List what changed since the last release:
   - the changes archived since then: folders in `waymark/changes/archive/` added after the tag (`git diff --name-only --diff-filter=A v<last>..origin/main -- waymark/changes/archive`), and each one's proposal, especially its Outcome and Impact;
   - `git log --oneline v<last>..origin/main`.
4. Check `## [Unreleased]` in `CHANGELOG.md` against those changes. Each change adds its own line there (charter rule 9), so name every archived change with a User-visible line that has none, and every behavior change that isn't labeled one.
5. List the findings those changes left open: the "Left open" part of each Outcome's `- Differs:` line, and the review findings in each task list's Log that no later item fixed. Show them grouped by change, and let the human decide each: fix before the release (through a change in the record), plan as a change for later, or drop.
6. Propose the version: a patch for fixes and small additions, a minor for new commands, behavior changes or a new record format. The human confirms it.

## 2. Prepare

On a new branch `release-v<version>` from `origin/main`:

1. Set `__version__` in `src/waymark/__init__.py`.
2. Set `wm_version` in `waymark/config.toml` to the same version. Reinstall the dev tool (`uv tool install --editable . --force`) and run `wm update`; review what it changed.
3. Turn `## [Unreleased]` in `CHANGELOG.md` into the entry: `## [<version>] - <today, YYYY-MM-DD>`, then a one-line summary, then its bold-labeled bullets, with the lines the audit found missing added. Put behavior changes first and name them plainly. If the record format changed, say whether `wm` reads an older record, migrates it, or refuses it and what to do then. Follow the `waymark-write-docs` style. The next change opens a new `## [Unreleased]` section.
4. Run `uv run --no-sync python -m tools.docs`.
5. Offer the `waymark-check-docs` skill on the docs pages changed since the last tag (`git diff --name-only v<last>..HEAD -- README.md docs`). Run it only if the human wants it, and fix what it finds through a change, or on this branch for wording alone.

## 3. Checks

All must pass:

```
uv run --no-sync pytest
uv run --no-sync ruff format --check .
uv run --no-sync ruff check .
uv run --no-sync mypy
uv run --no-sync codespell
uv run --no-sync python -m tools.docs --check
wm check
```

Where `uv run --no-sync pytest`, `mypy` or `codespell` fails to start with "uv trampoline failed to canonicalize script path" (seen on Windows), run them as modules instead: `uv run --no-sync python -m pytest`, `python -m mypy`, `python -m codespell_lib`. That is the tool failing to start, not a failing check.

## 4. Smoke test (the human)

Stop here. Ask the human to run `docs/smoke-test.md` with this version, in a scratch repository, and tell you the date, the Claude Code version (`claude --version`) and the operating system, plus anything that failed.

When they report back:
- add `Smoke test: passed on <date> with Claude Code <version> on <operating system>.` as the last line of the entry, listing anything that failed and how it was fixed;
- set the README's "Version last verified" to that Claude Code version.

A failure that needs a code fix goes through a change in the record, not into the release branch.

## 5. Pull request

1. `uv run --no-sync python -m tools.release check v<version>` must print no problems.
2. Commit with `chore(release): v<version>` and push the branch.
3. Open the pull request with `gh pr create`, titled `chore(release): v<version>`, with the changelog entry as its body.
4. Stop. The human reviews and merges it.

## 6. Tag (only on the human's word)

When the human says the pull request is merged and tells you to tag:

1. `git checkout main && git pull --ff-only`. The merged release commit must be on `main`, and `tools.release check v<version>` must still pass there.
2. `git tag v<version>` on that commit, then `git push origin v<version>`.

## 7. Verify

1. Watch the release workflow: `gh run list --workflow release.yml --limit 1`, then `gh run watch <id>`. Its publish job waits for a reviewer to approve the `pypi` environment's deployment. Tell the human it is waiting, and let them approve it in GitHub; never approve it yourself.
2. Check that PyPI has `waymark-cli==<version>` and that the GitHub release shows the changelog entry (`gh release view v<version>`).
3. Check CI on `main` for the release commit. A job that GitHub could not give a runner, such as "The job was not acquired by Runner", or a run canceled by a newer one, is not a failing check: with the human's yes, re-run it (`gh run rerun <id>`) and report how it ends.
4. Delete the merged release branch locally, and run `git fetch --prune`. Report the release's link.

## Rules

- Never push a tag, merge a pull request, or publish without the human's explicit go-ahead in this conversation.
- Never force-push, move or delete a tag, or release a version that already exists.
- Never edit the smoke-test line from anything but the human's own report.
- If a check fails, stop and report it; don't loosen the check.

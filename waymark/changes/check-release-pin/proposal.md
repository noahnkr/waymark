# Check release pin

Owner: Noah Roberts
Path: short
Accepted: 2026-11-15 by Noah Roberts (fingerprint: 4ba87b480cc42c09)

## Why

Waymark now develops itself with its own record, which pins the `wm` version in `waymark/config.toml`. Each release has to move that pin along with `__version__`, or the released repository is pinned to an older `wm`. Then `wm check` in CI and every write command on a fresh clone refuse until someone fixes the pin by hand. The `waymark-release` skill says to set both, but nothing checks it before the tag is pushed.

## What changes

- `python -m tools.release check <tag>` also refuses when `wm_version` in `waymark/config.toml` isn't the package version, or when the file or the key is missing. The message names both versions and says to set the pin and run `wm update`.
- The release workflow runs that check already, so a tag with a stale pin fails before anything is built or published.

## Non-goals

- Setting the pin for the maintainer. The `waymark-release` skill does that.
- Checking pins in other projects; this is Waymark's own release tooling.

## Impact

No spec changes. This is maintainer tooling in `tools/release.py`, not behavior of `wm`. Its tests are in `tests/test_docs.py`.

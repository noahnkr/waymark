# Tasks

## 1. Release check

- [x] 1.1 Refuse a release whose record pin doesn't match the package version
  - Criteria: `tools.release.problems` takes the pin read from `waymark/config.toml` (`wm_version`, parsed with `tomllib`) and adds a problem naming both versions when it differs from the package version, saying to set the pin and run `wm update`; a missing file or key is reported as a problem too; `python -m tools.release check <tag>` reads the pin from the repository's `waymark/config.toml`; the existing checks are unchanged
  - Verify: `tests/test_docs.py` covers a matching pin (no problem), a different pin, and a missing pin; `python -m tools.release check v0.1.0` on this repository reports no pin problem; the full checks pass
  - (note) 2026-11-15: self-review: tools.release reads wm_version from waymark/config.toml with tomllib and refuses a missing or different pin, naming both versions and saying to set it and run wm update; existing checks unchanged; tests cover matching, different and missing pins (15 pass), check v0.1.0 here reports ready, mypy clean.

## Log

- (accepted) 2026-11-15 fingerprint 4ba87b480cc42c09 items 1.1 by Noah Roberts

# Atlas

## Purpose

How a code repo of an atlas is tied to it: the pointer the code repo carries, and how `wm` finds the atlas from it. The registry and path hints are described with the multi-repo guide.

## Requirements

### Requirement: Pointer in the code repo's settings
A code repo SHALL point at its atlas through a pointer-only `waymark/config.toml`, holding the atlas's name, an optional path hint relative to the code repo, and the pinned `wm` version, and no record. `wm atlas point` SHALL write it. Commands run in a code repo with a pointer SHALL act on its atlas, and `wm check` there SHALL NOT report the code repo's `waymark/` as a broken record. `wm init` in a code repo with a pointer SHALL refuse without writing anything, naming the atlas and saying to run `wm init` there.

#### Scenario: Point a code repo
- GIVEN an atlas named `notes` beside a code repo `notes-api`
- WHEN `wm atlas point notes` runs in `notes-api`
- THEN `notes-api/waymark/config.toml` names the atlas `notes`, a path hint `../notes-atlas` and the pin, and `notes-api` has no other `waymark/` file and no `.waymark/` folder

#### Scenario: Commands act on the atlas
- GIVEN a code repo whose `waymark/config.toml` points at the atlas `notes`
- WHEN `wm status` runs in the code repo
- THEN it shows the atlas's changes

#### Scenario: Check in a code repo
- GIVEN a code repo whose `waymark/config.toml` points at an atlas whose record is healthy
- WHEN `wm check` runs in the code repo
- THEN it checks the atlas's record and reports it healthy

#### Scenario: Init in a code repo
- GIVEN a code repo whose `waymark/config.toml` points at the atlas `notes`
- WHEN `wm init` runs in it
- THEN it is refused, nothing is written, and the message names `notes` and says to run `wm init` in the atlas

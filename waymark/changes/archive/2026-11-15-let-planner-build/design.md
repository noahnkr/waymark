# Let planner build: design

## Context

- **Item tags.** `record/tasks.py` reads one trailing tag from an item's line, `` `review: <level>` ``, with `_LEVEL_TAG`. It strips the tag from the title and stores it as `Item.level_tag`. An unknown value is a problem, `unknown-review-level`, which `wm check` reports.
- **Fingerprint.** `record/fingerprint.py` builds each item's part from its title, level, criteria, verification and repo. Acceptance is withdrawn when the fingerprint changes.
- **Apply guidance.** In `services/instructions.py`, `_working` returns the same guidance for every item at `StepKind.APPLY`: start an implementer, and build the item yourself only if the tool has no isolated agents.
- **Atlas edits.** In `hooks/decide.py`, `_outside_record` refuses every planner edit inside a code repo. `working_repos` already works out which repo each accepted change's next item names, for implementers.
- **Prose.** The `wm-apply` skill opens with "You don't write the code yourself", and `docs/concepts.md` says "Code is always built by an implementer". The charter's vision and its apply rule assume the same.

## Approach

1. **Tag parsing.** Read the trailing tags in a loop, so `review:` and `build:` can appear in either order and each at most once. Add `Item.delegate: bool`. An unknown `build:` value is a problem, `unknown-build-tag`. A tag given twice is a problem, `repeated-tag`. The title is what is left once the tags are removed.
2. **Fingerprint.** Append `delegate` to an item's definition only when the tag is present. An untagged item then fingerprints exactly as before, so upgrading `wm` doesn't withdraw any existing acceptance.
3. **Instructions.** Split the `APPLY` branch of `_working` in two:
   - **Untagged:** build the item from `wm context <change> <item> --for implement`, run the checks it touches, then record the result with `wm tick`, `wm block` or `wm gap`. The commands list those three.
   - **Tagged:** today's guidance, start an implementer with the change and item.
   - `wm reopen` stays first in both when a review asked for changes.
4. **JSON.** The item in `wm show --json` gains `"delegate": bool`, and `views/schemas.py` and `docs/json.md` follow. Adding a field keeps the schema version.
5. **Atlas hook.** Rename `working_repos` to a neutral name, since it is no longer only for implementers. The planner branch of `_outside_record` then uses it as the implementer branch does:
   - allowed inside a repo that the next item of an accepted change names;
   - refused elsewhere, with the repos it may edit now.
6. **Assets.**
   - `wm-apply`: the planner builds by default, and delegates only tagged items.
   - `wm-propose`: suggest `build: delegate` for large or parallel items, as review levels are suggested.
   - `wm-update`: mention that changing the tag withdraws acceptance.
   - `wm-onboard`: describe the default.
   - `wm-implementer`: the definition says it is started only for delegated items.
7. **Charter and docs.**
   - The charter's vision line and its goal "Agents work only from what is written down".
   - The apply rule: run the checks the item touches, and the full checks once before the pull request.
   - Concepts (the roles table, the tag and the gates), getting started, the multi-repo guide, the smoke test, architecture and the README.
   - Regenerate the generated docs.

## Decisions

### Decision: How delegation is marked
- **Options:**
  - a `build: delegate` tag on the item;
  - the planner decides at apply, with nothing in the record;
  - an item field line, `Build: delegate`.
- **Choice:** a `build: delegate` tag.
- **Why:** The human sees it and confirms it at accept, and it follows the `review:` tag the format already has. A field line would add a fourth labeled line for what is a yes or no.

### Decision: Whether the tag is enforced
- **Options:**
  - the hooks refuse planner edits while a tagged item is being built;
  - guidance only.
- **Choice:** guidance only.
- **Why:** The hook can't tell which item a planner edit belongs to, and the planner also edits the record during apply. Refusing all code edits while a tagged item is next would block legitimate fixes. The tag decides what `wm instructions` and the skills say, as review levels do for the self-review.

### Decision: Keeping existing acceptances valid
- **Options:**
  - add the delegate flag to every item's fingerprint part;
  - add it only when the tag is present.
- **Choice:** only when present.
- **Why:** Adding it everywhere would change the fingerprint of every accepted change in every project on upgrade, and withdraw acceptance with nothing having changed.

### Decision: Planner edits in an atlas
- **Options:**
  - the same rule as implementers;
  - any code repo.
- **Choice:** the same rule as implementers (the human chose it).
- **Why:** It keeps the atlas guard rail that code changes happen only for an accepted item, and it reuses `working_repos`.

## Risks and trade-offs

- **The cold-start check is given up.** An untagged item no longer proves that the record is enough to build from. The planner may lean on what was said in the session and not written down. The `wm-apply` skill tells the planner to write any such fact into the record, as a spec gap or a revision, before building on it.
- **The planner reviews its own work.** At review level `self`, the agent that built the item now also reviews it. Riskier items keep `review: independent`, and `review-per-change` revisits review next.
- **Long sessions.** Building many items in one session grows the planner's context. Tagging large items for delegation is the release valve.

# Tasks

## 1. Record

- [x] 1.1 Read and check resources
  - Criteria:
    - `record/resources.py` reads a resource's title, the lines `- Kind:`, `- Serves:`, `- Status:` and `- Verified:`, the six sections, and the outline of its `##` and `###` headings; `load_record` loads `resources/` into `Record.resources`, and `Record.documents()` yields them
    - `wm check` reports as an error a missing line or section (naming it), a kind other than the six (listing them), a status other than `active` or `retired`, and a `- Verified:` value not in `YYYY-MM-DD` (saying so), each on its line where there is one
    - `wm check` reports as an error a `- Serves:` name that isn't a spec, naming it and listing the specs; `none` names no spec
    - a complete resource whose Interface holds only `None.` is reported healthy
  - Verify:
    - `test_scenario_complete_resource`, `test_scenario_missing_section`, `test_scenario_date_in_another_form`, `test_scenario_unknown_kind` and `test_scenario_unknown_spec` in a new `tests/record/test_resources.py`
    - `wm check` passes on this repository
- [x] 1.2 Keep `resources/` in git
  - Criteria:
    - `resources` is in `RECORD_FOLDERS`, so `wm init` writes `resources/.gitkeep` in a new record, and `wm update` writes it when it is missing and lists `created: waymark/resources/.gitkeep`
    - this repository's record gets `waymark/resources/.gitkeep` in the same commit
  - Verify:
    - the existing tests for the scenarios New record, Existing record without them, Already in place and Last change archived, updated for seven folders, and `test_scenario_record_without_resources`, in `tests/services/test_setup.py` or beside them
- [ ] 1.3 `wm new resource`
  - Criteria:
    - `templates/resource.md` holds the title, the four lines, a comment with the rule never to store secrets and a good and bad example, and the six sections, each with a comment saying what goes there, to write `None.` when it doesn't apply, and that environments go in `###` subsections
    - `wm new resource <name> <kind>` writes `resources/<name>.md` with `- Kind: <kind>`, `- Serves: none`, `- Status: active` and `- Verified: <today>`, prints `Created the resource "<name>".`, and the new file passes `wm check`
    - it refuses a name that is already a resource, leaving the file unchanged, and a missing or unknown kind, listing the six and writing nothing; `wm new change`, `milestone` and `exploration` refuse a kind argument
  - Verify:
    - `test_scenario_new_resource`, `test_scenario_name_taken` and `test_scenario_unknown_kind_given` in `tests/services/test_setup.py`
- [ ] 1.4 `wm ls resources` and `wm show --kind resource`
  - Criteria:
    - `wm ls resources` lists every resource with its kind, status and the specs it serves (`none` when it serves none), in text and as JSON
    - `wm show <name> --kind resource` shows the resource in full, in text and as a new `wm.show.resource` JSON payload described in `views/schemas.py`
  - Verify:
    - `test_scenario_listing` in `tests/test_views_cli.py`, and a test that `wm show --kind resource --json` validates against its schema with `tests/views/validator.py`

## 2. Agents

- [ ] 2.1 Resources in the context packs
  - Criteria:
    - the explore pack holds `resources`: each resource's name, title, kind, status and served specs, retired ones included
    - the implement and review packs hold `resources`: each active resource serving a spec the change has a delta for, with its name, kind, What it is and Access text, the outline of its other headings, and the command `wm show <name> --kind resource`; nothing of a retired resource, or of one serving only other specs
    - the text output renders the same resources as the JSON, and no schema version changes
  - Verify:
    - `test_scenario_serving_resource_in_the_implement_pack`, `test_scenario_resource_for_another_spec`, `test_scenario_retired_resource` and `test_scenario_explore_index`, beside the existing context-pack tests
- [ ] 2.2 Resources in the edit guard
  - Criteria:
    - a planner's edit, creation or removal under `resources/` is allowed, with or without a change in flight
    - an implementer's edit under `resources/` is allowed; any other implementer edit in the record is still refused with the reason that an implementer doesn't edit the record, and its hand-written notes with a reason naming `wm note`
    - a reviewer's edit of a resource is refused with the reason that a reviewer edits nothing
  - Verify:
    - `test_scenario_planner_edits_outside_a_change`, `test_scenario_implementer_edits_a_resource`, `test_scenario_reviewer_edits_a_resource`, `test_scenario_implementer_edits_a_proposal` and `test_scenario_resource_updated_as_tiny_work` in `tests/hooks/test_decide.py`, and the existing tests for Implementer writes a note by hand, Code edited outside a change, Spec edited outside a change and Nothing recorded still pass
- [ ] 2.3 The resource rule in the tasks guidance
  - Criteria: `wm instructions` for the tasks step gives, among its sizing rules, "Give a change that sets up or alters something outside the repo an item to create or update its resource.", and the specs-step and other tasks-step rules are unchanged
  - Verify: `test_scenario_resource_item` beside the existing tests for the scenarios Specs step and Tasks step

## 3. Skills and docs

- [ ] 3.1 Skills that know about resources
  - Criteria:
    - `wm-propose` says a fact about an outside system belongs in a resource, not a spec, and that a change that sets up or alters something outside the repo gets an item to create or update its resource
    - `wm-explore` says to read the resources the explore pack lists when the idea touches one
    - `wm-apply` says to update the resource and its `- Verified:` date when an item changes something outside the repo
    - each skill keeps the shared layout the `skills` spec requires
  - Verify: `uv run --no-sync pytest tests/test_skills.py tests/adapters` passes, with any snapshots regenerated
- [ ] 3.2 Docs for resources
  - Criteria:
    - `docs/record.md` has a Resource section (folder, the four lines, the six sections, kinds, who edits it, the rule never to store secrets) and shows `resources/` in its tree and among the folders with a `.gitkeep`
    - `docs/concepts.md` defines a resource, and how it differs from a spec
    - `docs/cli.md` and `docs/json.md` are regenerated, and the CHANGELOG's Unreleased section names the new note, commands and pack fields
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py` and codespell pass

## Log

- (accepted) 2026-11-17 fingerprint 3ef36b267996b080 items 1.1 1.2 1.3 1.4 2.1 2.2 2.3 3.1 3.2 by Noah Roberts

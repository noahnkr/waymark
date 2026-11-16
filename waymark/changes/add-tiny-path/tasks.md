# Tasks

## 1. The tiny path

- [ ] 1.1 Let the planner edit any code repo in an atlas
  - Criteria: in an atlas, a planner edit in any code repo is allowed, whether or not a change is being built; an implementer's edit outside the repo its item names is refused as before; `editable_repos` is documented as the implementers' limit; edits to specs stay refused for every role
  - Verify: tests in `tests/hooks/test_decide.py` and `tests/hooks/test_repo_limits.py` for the scenarios "Repo of the item being built", "Another repo" and "Implementer in another repo"
- [ ] 1.2 Test that work outside a change is allowed and leaves no trace, and name the path tests after their scenarios
  - Criteria: tests cover the `paths` scenarios "Code edited outside a change", "Spec edited outside a change" and "Nothing recorded" with no change in flight; the existing short and full path tests cover "Design on the short path" and "Full path without a design", named after them
  - Verify: `uv run --no-sync pytest tests/hooks tests/record/test_state.py`
- [ ] 1.3 Add the `wm-fix` skill, and offer the three paths in the other skills
  - Criteria: `assets/skills/wm-fix/SKILL.md` runs the tiny path as the design describes (confirm no requirement changes, say why and wait for the human's yes, build on a branch, run the checks, conventional commit, offer a pull request, hand over to `wm-propose` if a requirement changes) and writes nothing to the record; it is listed in `assets/__init__.py` and copied by every adapter; `wm-propose` step 1 asks which path fits and hands tiny work to `wm-fix`; `wm-explore`'s closing offers include fixing on the tiny path; `wm-onboard` mentions the three paths; the planner runs `wm update`
  - Verify: `uv run --no-sync pytest tests/adapters`; read the new skill once through as the planner would
- [ ] 1.4 Ask for functional requirements at the specs step
  - Criteria: `wm instructions` at the specs step says that requirements describe what the system does as a user or another program sees it, and that files the user doesn't touch, internals and mechanisms go in the design; `wm-propose` says the same; the charter's `### specs` rules hold the same rule for Waymark
  - Verify: a test in `tests/services/test_agent_interface.py` for the specs guidance; `wm instructions specs`

## 2. Charter and docs

- [ ] 2.1 Describe the three paths in the charter and the docs
  - Criteria: the charter's goals name the tiny path's approval (the human's yes in the session, and the merge) and the three paths; concepts has a section on the tiny, short and full paths and its glossary has "Tiny path"; getting started, the multi-repo guide (the planner may edit any code repo), the smoke test (one tiny fix) and the README's "Light for small changes" match; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py`, `uv run --no-sync codespell` and `wm check`

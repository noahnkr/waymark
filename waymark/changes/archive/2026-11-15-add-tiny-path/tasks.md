# Tasks

## 1. The tiny path

- [x] 1.1 Let the planner edit any code repo in an atlas
  - Criteria: in an atlas, a planner edit in any code repo is allowed, whether or not a change is being built; an implementer's edit outside the repo its item names is refused as before; `editable_repos` is documented as the implementers' limit; edits to specs stay refused for every role
  - Verify: tests in `tests/hooks/test_decide.py` and `tests/hooks/test_repo_limits.py` for the scenarios "Repo of the item being built", "Another repo" and "Implementer in another repo"
- [x] 1.2 Test that work outside a change is allowed and leaves no trace, and name the path tests after their scenarios
  - Criteria: tests cover the `paths` scenarios "Code edited outside a change", "Spec edited outside a change" and "Nothing recorded" with no change in flight; the existing short and full path tests cover "Design on the short path" and "Full path without a design", named after them
  - Verify: `uv run --no-sync pytest tests/hooks tests/record/test_state.py`
- [x] 1.3 Add the `wm-fix` skill, and offer the three paths in the other skills
  - Criteria: `assets/skills/wm-fix/SKILL.md` runs the tiny path as the design describes (confirm no requirement changes, say why and wait for the human's yes, build on a branch, run the checks, conventional commit, offer a pull request, hand over to `wm-propose` if a requirement changes) and writes nothing to the record; in an atlas it is run from the atlas session, uses a branch of the same name in each code repo the fix touches, commits in each and offers one pull request per repo; it is listed in `assets/__init__.py` and copied by every adapter; `wm-propose` step 1 asks which path fits and hands tiny work to `wm-fix`; `wm-explore`'s closing offers include fixing on the tiny path; `wm-onboard` mentions the three paths; the planner runs `wm update`
  - Verify: `uv run --no-sync pytest tests/adapters`; read the new skill once through as the planner would
- [x] 1.4 Ask for functional requirements at the specs step
  - Criteria: `wm instructions` at the specs step says that requirements describe what the system does as a user or another program sees it, and that files the user doesn't touch, internals and mechanisms go in the design; `wm-propose` says the same; the charter's `### specs` rules hold the same rule for Waymark
  - Verify: a test in `tests/services/test_agent_interface.py` for the specs guidance; `wm instructions specs`

## 2. Charter and docs

- [x] 2.1 Describe the three paths in the charter and the docs
  - Criteria: the charter's goals name the tiny path's approval (the human's yes in the session, and the merge) and the three paths; concepts has a section on the tiny, short and full paths and its glossary has "Tiny path"; getting started, the multi-repo guide (the planner may edit any code repo), the smoke test (one tiny fix) and the README's "Light for small changes" match; the docs follow the `waymark-write-docs` skill
  - Verify: `uv run --no-sync python -m tools.docs --check`, `uv run --no-sync pytest tests/test_docs.py`, `uv run --no-sync codespell` and `wm check`

## Review

- (review) 2026-11-15 pass: every item's criteria hold and every delta scenario is met, the full suite (932 tests), docs check, codespell, ruff, mypy and wm check all pass, and the atlas edit rule, wm-fix skill, specs guidance and docs follow the design
  - suggestion: tests/services/test_check.py test_nothing_recorded: it commits through `commit_all` and never checks that the message is conventional, which the "Nothing recorded" scenario mentions; it checks the record, `wm check` and `wm status` only
  - suggestion: tests/hooks/test_decide.py test_spec_edited_outside_a_change: it asserts the reason "they change only when a change is archived or synced", which is close to the scenario's "specs change only through a change" but not the same words; consider aligning the scenario wording or the refusal text
  - suggestion: docs/multi-repo.md:150: the edited paragraph leaves one line far longer than the lines around it; rewrap it
  - suggestion: CHANGELOG.md: no line yet for the behavior changes the proposal marks "for the changelog" (wm-fix, planner edits in an atlas, the specs guidance); the waymark-write-docs skill asks for one, though earlier changes left this to the release commit

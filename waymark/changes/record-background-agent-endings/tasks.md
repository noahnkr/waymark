# Tasks

## 1. Agent markers

- [x] 1.1 Keep a marker per agent in the clone's git folder, in `record/agents.py`
  - Criteria: functions mark an agent's ending as recorded, count a refused attempt, read an agent's marker and remove it; markers live under `<git dir>/waymark/agents/<agent_id>`, found through a `git` helper that works in a worktree; an `agent_id` that isn't letters, digits, `-` or `_` is ignored; writing a marker removes markers older than a day; nothing is written outside the git folder
  - Verify: tests in `tests/record/test_agents.py`, including a worktree, an unsafe `agent_id`, and the sweep of an old marker
  - Note: API for 2.1: `read_marker(where, agent_id) -> Marker | None` (`Marker.recorded`, `Marker.attempts`), `mark_recorded`, `count_attempt` (returns the new count; 0 for an unusable id or outside a repo) and `remove_marker`, each taking any folder in the repo; the folder comes from the new `git.git_path(folder, relative)`.
  - (self-review) 2026-11-15: record/agents.py keeps one marker per agent under the git folder found through git.git_path (worktree-aware); read, mark recorded, count attempts and remove work; unsafe ids and folders outside a repo do nothing; writing sweeps markers older than a day. Its 20 tests and the boundary tests pass.

## 2. Recording handbacks

- [x] 2.1 Record an ending from a handed-back report in the core   `review: independent`
  - Criteria: a `HANDBACK` event and `agent_id` on `AGENT_STOP` exist in `hooks/events.py`; a handback with an ending records it exactly as a final message would, and marks the agent; a handback without one is refused with the ending reason, and on the second refusal allowed with a notice to record the result by hand; `AGENT_STOP` for an agent with a marker is allowed without reading the message, and the marker removed; `AGENT_STOP` without a marker behaves as before
  - Verify: tests in `tests/hooks/test_decide.py` for every scenario of the `agent-results` delta: final message, background implementer, background reviewer, report without an ending, stop after a recorded handback
  - Note: for 2.2: `Event(EventKind.HANDBACK, cwd, role, message=..., agent_id=...)`; `AGENT_STOP` takes `agent_id=` too. Markers are keyed on `project.root`. A stop whose marker holds only one refused attempt still needs its ending, as the design says ("Otherwise it behaves as today"); the marker is removed whenever the stop is let through.
  - (review) 2026-11-15 pass: HANDBACK and AGENT_STOP agent_id are in events.py; a handback is recorded through the same _record as a final message and marks the agent; a report without an ending is refused with the ending reason and let through with a notice on the second refusal; a stop after a recorded or given-up handback is allowed unread and its marker removed, and other stops behave as before; every agent-results scenario is tested and pytest (799), ruff and mypy pass.
- [x] 2.2 Map Claude Code's handback, and let the agents use it   `review: independent`
  - Criteria: `PreToolUse` on `SubagentHandback` becomes a `HANDBACK` event with the report from `tool_input.message`, the role from `agent_type` and `agent_id`; `SubagentStop` carries `agent_id`; a refused handback becomes a `PreToolUse` deny with the reason; the `PreToolUse` matcher includes `SubagentHandback`; neither agent definition forbids it; the settings and agent snapshots are updated
  - Verify: tests in `tests/adapters/test_claude_code.py` with a handback payload for each role, a refused one, and the updated snapshots; a test runs `wm hook claude-code PreToolUse` with a handback payload in a project and the item is ticked
  - Note: this checkout's own `.claude/` files still hold the old matcher and `disallowedTools` until `wm update` is run; they are ignored by git, so nothing in the change covers them.
  - (review) 2026-11-15 pass: SubagentHandback on PreToolUse becomes a HANDBACK event (report from tool_input.message, role from agent_type, agent_id), SubagentStop passes agent_id, a refused handback becomes a PreToolUse deny with the reason, the matcher includes SubagentHandback, neither agent definition forbids it, the snapshots are updated, and the tests run wm hook for each role, a refused report and a stop after a recorded handback; pytest (806), ruff and mypy pass.

## 3. Docs

- [x] 3.1 Update the smoke test and the architecture notes   `review: none`
  - Criteria: `docs/smoke-test.md` checks that the ending is recorded for an implementer in the background and for one in the foreground, saying how to ask for each; `docs/architecture.md` lists the handback among the neutral events; the docs follow the `waymark-write-docs` skill
  - Verify: `python -m tools.docs --check`, `pytest tests/test_docs.py` and `codespell` pass

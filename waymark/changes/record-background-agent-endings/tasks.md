# Tasks

## 1. Agent markers

- [ ] 1.1 Keep a marker per agent in the clone's git folder, in `record/agents.py`
  - Criteria: functions mark an agent's ending as recorded, count a refused attempt, read an agent's marker and remove it; markers live under `<git dir>/waymark/agents/<agent_id>`, found through a `git` helper that works in a worktree; an `agent_id` that isn't letters, digits, `-` or `_` is ignored; writing a marker removes markers older than a day; nothing is written outside the git folder
  - Verify: tests in `tests/record/test_agents.py`, including a worktree, an unsafe `agent_id`, and the sweep of an old marker

## 2. Recording handbacks

- [ ] 2.1 Record an ending from a handed-back report in the core   `review: independent`
  - Criteria: a `HANDBACK` event and `agent_id` on `AGENT_STOP` exist in `hooks/events.py`; a handback with an ending records it exactly as a final message would, and marks the agent; a handback without one is refused with the ending reason, and on the second refusal allowed with a notice to record the result by hand; `AGENT_STOP` for an agent with a marker is allowed without reading the message, and the marker removed; `AGENT_STOP` without a marker behaves as before
  - Verify: tests in `tests/hooks/test_decide.py` for every scenario of the `agent-results` delta: final message, background implementer, background reviewer, report without an ending, stop after a recorded handback
- [ ] 2.2 Map Claude Code's handback, and let the agents use it   `review: independent`
  - Criteria: `PreToolUse` on `SubagentHandback` becomes a `HANDBACK` event with the report from `tool_input.message`, the role from `agent_type` and `agent_id`; `SubagentStop` carries `agent_id`; a refused handback becomes a `PreToolUse` deny with the reason; the `PreToolUse` matcher includes `SubagentHandback`; neither agent definition forbids it; the settings and agent snapshots are updated
  - Verify: tests in `tests/adapters/test_claude_code.py` with a handback payload for each role, a refused one, and the updated snapshots; a test runs `wm hook claude-code PreToolUse` with a handback payload in a project and the item is ticked

## 3. Docs

- [ ] 3.1 Update the smoke test and the architecture notes   `review: none`
  - Criteria: `docs/smoke-test.md` checks that the ending is recorded for an implementer in the background and for one in the foreground, saying how to ask for each; `docs/architecture.md` lists the handback among the neutral events; the docs follow the `waymark-write-docs` skill
  - Verify: `python -m tools.docs --check`, `pytest tests/test_docs.py` and `codespell` pass

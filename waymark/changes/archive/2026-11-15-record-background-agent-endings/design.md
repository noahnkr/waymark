# Record background agent endings: design

## Context

- `adapters/claude_code.py` maps Claude Code's hook payloads to neutral events.
  - `SubagentStop` becomes `AGENT_STOP`, with `message` taken from `last_assistant_message` and `retried` from `stop_hook_active`.
  - The `PreToolUse` matcher covers `Agent`, the edit tools and the shell tools.
  - The agent definitions set `disallowedTools` to include `SubagentHandback`, and that line didn't stop the agents from using it.
- `hooks/decide.py` `_agent_stop`:
  - parses the ending with `_record`, then ticks, blocks, notes a gap or writes the verdict through `services/lifecycle`;
  - when the ending is missing, refuses the first time and gives the planner a notice when `retried`.
- Role detection reads `agent_type` from each payload, and it already works for tool calls made inside a subagent. That's how the implementer's edits are limited today.
- The Claude Code hooks reference documents that:
  - a background subagent reports through `SubagentHandback`, whose `tool_input.message` holds the report;
  - `PreToolUse` and `PostToolUse` can match that tool;
  - `SubagentStop` still fires, with `last_assistant_message` holding only the closing text;
  - both payloads carry `agent_id`.
- Constraints:
  - only `record/` touches files;
  - only `adapters/` names a tool;
  - no cache: `wm` reads the files fresh on every run.

## Approach

1. **A new neutral event, `HANDBACK`,** with `role`, `message` (the report) and `agent_id`. `AGENT_STOP` also gains `agent_id`. `hooks/events.py` documents both.
2. **The adapter** maps `PreToolUse` on `SubagentHandback` to `HANDBACK`, with `message=tool_input.message` and `agent_id`. It adds `SubagentHandback` to the `PreToolUse` matcher and removes it from both agents' `disallowedTools`.
   - Implementer: `Agent`.
   - Reviewer: `Edit, Write, MultiEdit, NotebookEdit, Agent`.

   It also maps `agent_id` for `SubagentStop`. A refused `HANDBACK` becomes a `PreToolUse` deny with the reason, as for other tools.
3. **The core.**
   - `_handback(project, event, today)` records the ending through `_record`, the same as `_agent_stop`. On success it writes a marker for `event.agent_id` and allows the tool. Without an ending it refuses with `_ending(role)`, and counts the attempt in the marker. On the second refusal it allows the tool, with a notice telling the planner to record the result with the `wm` commands.
   - `_agent_stop` first checks for a marker for `event.agent_id`. When the handback was recorded, or already given up on, it removes the marker and allows the stop without reading the message. Otherwise it behaves as today.
4. **The markers.** A new module `record/agents.py` keeps a small file per agent at `<git dir>/waymark/agents/<agent_id>`, holding `recorded` or `attempts: <n>`. `git.git_path` gives the folder, so it works in worktrees.
   - The markers belong to the clone, are never committed, and are not read by any view.
   - An `agent_id` that isn't a plain identifier (letters, digits, `-`, `_`) is ignored, so a payload can't name a path.
   - Markers older than a day are removed when a new one is written.
5. **Settings.** The settings `wm init` and `wm update` write gain the matcher. The snapshot `tests/adapters/snapshots/settings.json` and the agent snapshots are updated.
6. **Docs.**
   - `docs/smoke-test.md`: the ending is recorded for an implementer run in the background, the default, and for one run in the foreground. The steps say how to ask for each.
   - `docs/architecture.md`, "How hook decisions work": seven neutral events, including the handback.

## Decisions

### Decision: Which event carries the handed-back report
- **Options:** `PreToolUse` on `SubagentHandback`; `PostToolUse` on it; reading the agent's transcript at `SubagentStop`.
- **Choice:** `PreToolUse`.
- **Why:**
  - Only `PreToolUse` can refuse, so an agent whose report lacks its ending is sent back to add it, exactly as `SubagentStop` does for a final message.
  - The transcript's format belongs to Claude Code and isn't documented as stable.

### Decision: How the stop knows a handback was recorded
- **Options:**
  - a marker per `agent_id` in the clone's git folder;
  - searching the record for evidence matching the agent's item, which the stop event can't name;
  - never refusing at `SubagentStop` when the message lacks an ending;
  - reading the transcript.
- **Choice:** a marker per `agent_id`.
- **Why:**
  - The stop event carries no item, so the record can't answer it.
  - Never refusing would break the foreground case, where the refusal is what makes agents end correctly.
  - A marker file in the git folder is per clone, never shared, and is written and read only by the hooks. It's state the hooks pass between two events, not a cache of the record.

### Decision: Keep `SubagentStop`
- **Options:** replace it with the handback; keep both.
- **Choice:** keep both.
- **Why:** foreground agents still end with a final message, and other modes or versions of Claude Code may not use the handback.

## Risks and trade-offs

- **`agent_type` may be missing from a subagent's `SubagentHandback` call.** Then the role is the planner, and nothing is recorded. The same field already drives the edit limits, and the smoke test checks it.
- **A marker can be left behind.** For example, if `SubagentStop` never fires. Markers are small and old ones are swept, and a stale marker only lets one stop through without asking.
- **Hidden state outside the record.** It's limited to the hooks' own bookkeeping, and the record stays the only source of evidence.
- **Claude Code may change the handback.** The smoke test catches it before a release.

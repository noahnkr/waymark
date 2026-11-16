# Record background agent endings

Owner: Noah Roberts

## Why

`wm` writes an item's evidence from the implementer's and reviewer's own last lines: `ITEM:` then `RESULT:` or `VERDICT:`. In Claude Code, the `SubagentStop` hook reads them from `last_assistant_message`. Agents that Claude Code runs in the background report through the `SubagentHandback` tool instead. The Claude Code hooks reference says `last_assistant_message` then holds only the agent's closing text, "which is not the delivered report." The report itself is in the tool's `tool_input.message`.

So no result was recorded for any of the 11 agent runs of `keep-agent-setup-local`: 7 implementers and 4 reviewers. The planner recorded every tick and verdict by hand. The `disallowedTools: SubagentHandback` line in the agent definitions didn't stop the agents from using the tool. This is the smoke test's check that results are recorded from the agent's final message (G46). Until it is fixed, evidence written only by `wm` from an agent's own words doesn't hold in Claude Code's default mode, so it has to be fixed before 0.1.1.

## What changes

- **A report handed back through `SubagentHandback` is recorded.** The Claude Code adapter listens for it, and the core records the ending from the report's text, the same way as from a final message. A report without the two lines is refused with the same reason, so the agent hands back again with them.
- **`SubagentStop` doesn't ask again for a report that was handed back.** When an agent's ending was already recorded from its handback, the stop is allowed without refusing the closing text.
- **The agent definitions stop forbidding `SubagentHandback`,** because the line doesn't work and the tool is now how background agents report.
- **The smoke test** checks the ending is recorded for an agent run in the background and for one run in the foreground.

## Non-goals

- Forcing agents into the foreground.
- Recording results from tools other than Claude Code. They have no hooks, and the skills already tell the planner to record results with the `wm` commands.
- Changing the ending's format or what each result word records.

## Impact

- New spec: `agent-results` (recording an agent's result from its ending, however it hands its report back).
- Users see that ticks and verdicts are recorded again in Claude Code when agents run in the background, as they do by default. That's a fix, for the changelog.
- Code: `adapters/claude_code.py` (hook events and the agent definitions), `hooks/events.py` and `hooks/decide.py`, and the settings that `wm update` and `wm init` render.
- Docs: `docs/smoke-test.md`, and `docs/architecture.md` where it describes the agent stop.

## Outcome

Claude Code agents running in the background now have their results recorded. The adapter reads the report an agent hands back through SubagentHandback, the core records its ending exactly as from a final message, and a per-agent marker in the clone's git folder lets the following stop through without asking again. A stop after a single refused handback still asks for the ending, as the design says. A handback without an agent_id is refused every time; the smoke test checks that Claude Code sends one.

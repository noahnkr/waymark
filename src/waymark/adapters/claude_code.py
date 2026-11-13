"""The Claude Code adapter.

It copies the skills into ``.claude/skills/``, writes the two agent
definitions into ``.claude/agents/``, and merges wm's hooks into
``.claude/settings.json``. Its hook handler turns Claude Code's hook payloads
into wm's neutral events and the decisions back into Claude Code's replies.
It decides nothing itself.
"""

import datetime
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from waymark import assets
from waymark.adapters import Adapter, Capabilities, HookReply
from waymark.hooks.decide import decide
from waymark.hooks.events import Decision, Event, EventKind, Replacement, Role

NAME = "claude-code"
SETTINGS = ".claude/settings.json"
LOCAL_SETTINGS = ".claude/settings.local.json"
"""Per-machine settings, never committed; the code repos of an atlas are attached here."""
HOOK_COMMAND = f"wm hook {NAME}"
HOOK_TIMEOUT = 60

_EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
_SHELL_TOOLS = ("Bash", "PowerShell")
_ROLES = {assets.IMPLEMENTER: Role.IMPLEMENTER, assets.REVIEWER: Role.REVIEWER}
_AGENT_TOOLS = {
    assets.IMPLEMENTER: "Agent, SubagentHandback",
    assets.REVIEWER: "Edit, Write, MultiEdit, NotebookEdit, Agent, SubagentHandback",
}
"""The tools each agent goes without. Neither may start agents of its own, and
neither hands its report back through a tool: the report must be its final
message, where the stop hook reads its ending."""

_HOOKS: dict[str, str | None] = {
    "SessionStart": None,
    "PreToolUse": "|".join(("Agent", *_EDIT_TOOLS, *_SHELL_TOOLS)),
    "PostToolUse": "Edit|Write|MultiEdit",
    "SubagentStop": "|".join(assets.AGENTS),
}
"""The hook events wm listens to, each with the matcher that selects what it handles."""


def _agent_file(name: str) -> str:
    description, body = assets.agent(name)
    header = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"disallowedTools: {_AGENT_TOOLS[name]}",
        "---",
    ]
    return "\n".join(header) + "\n\n" + body


def _is_ours(handler: Any) -> bool:
    command = handler.get("command", "") if isinstance(handler, dict) else ""
    return isinstance(command, str) and command.startswith("wm hook ")


def merge_settings(existing: str | None) -> str:
    """The settings file with wm's hooks in place and everything else as it was.

    Only hook entries whose command starts with ``wm hook`` are replaced. The
    file is written back as JSON with two-space indentation.
    """
    settings = json.loads(existing) if existing and existing.strip() else {}
    if not isinstance(settings, dict):
        raise ValueError("the top level is not an object")
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError('"hooks" is not an object')
    merged: dict[str, list[Any]] = {}
    for event, groups in hooks.items():
        kept: list[Any] = []
        for group in groups if isinstance(groups, list) else []:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                kept.append(group)
                continue
            theirs = [handler for handler in handlers if not _is_ours(handler)]
            if theirs:
                kept.append({**group, "hooks": theirs})
        if kept:
            merged[event] = kept
    for event, matcher in _HOOKS.items():
        handler = {"type": "command", "command": f"{HOOK_COMMAND} {event}", "timeout": HOOK_TIMEOUT}
        ours: dict[str, Any] = {"hooks": [handler]}
        if matcher is not None:
            ours = {"matcher": matcher, **ours}
        merged.setdefault(event, []).append(ours)
    return json.dumps({**settings, "hooks": merged}, indent=2, ensure_ascii=False) + "\n"


def merge_local_settings(existing: str | None, folders: Sequence[Path]) -> str:
    """The per-machine settings with the code repo folders attached, everything else kept.

    Folders are added to ``permissions.additionalDirectories`` when missing.
    Nothing is removed: the file can't tell wm's entries from the person's own.
    """
    settings = json.loads(existing) if existing and existing.strip() else {}
    if not isinstance(settings, dict):
        raise ValueError("the top level is not an object")
    permissions = settings.get("permissions", {})
    if not isinstance(permissions, dict):
        raise ValueError('"permissions" is not an object')
    listed = permissions.get("additionalDirectories", [])
    if not isinstance(listed, list):
        raise ValueError('"permissions.additionalDirectories" is not a list')
    seen = {Path(entry) for entry in listed if isinstance(entry, str)}
    added = [str(folder) for folder in folders if folder not in seen]
    permissions = {**permissions, "additionalDirectories": [*listed, *added]}
    return json.dumps({**settings, "permissions": permissions}, indent=2, ensure_ascii=False) + "\n"


def _role(payload: Mapping[str, Any]) -> Role:
    return _ROLES.get(str(payload.get("agent_type") or ""), Role.PLANNER)


def _path(value: Any, cwd: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else cwd / path


def _edit_event(kind: EventKind, payload: Mapping[str, Any], cwd: Path) -> Event:
    tool_input = payload.get("tool_input") or {}
    path = _path(tool_input.get("file_path") or tool_input.get("notebook_path"), cwd)
    content = tool_input.get("content") if payload.get("tool_name") == "Write" else None
    edits = tool_input.get("edits") or [tool_input]
    replacements = tuple(
        Replacement(
            str(edit["old_string"]), str(edit.get("new_string", "")), bool(edit.get("replace_all"))
        )
        for edit in edits
        if isinstance(edit, dict) and "old_string" in edit
    )
    return Event(
        kind,
        cwd,
        _role(payload),
        path=path,
        content=content if isinstance(content, str) else None,
        replacements=replacements,
    )


def _event(  # noqa: PLR0911 - one return per hook event
    name: str, payload: Mapping[str, Any], cwd: Path
) -> Event | None:
    """Claude Code's hook payload as one of wm's neutral events; None when it isn't ours."""
    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    role = _role(payload)
    if name == "SessionStart":
        return Event(EventKind.SESSION_START, cwd)
    if name == "SubagentStop":
        return Event(
            EventKind.AGENT_STOP,
            cwd,
            role,
            message=str(payload.get("last_assistant_message") or ""),
            retried=bool(payload.get("stop_hook_active")),
        )
    if name == "PreToolUse" and tool == "Agent":
        return Event(
            EventKind.DELEGATE,
            cwd,
            role,
            agent=str(tool_input.get("subagent_type") or ""),
            prompt=str(tool_input.get("prompt") or ""),
        )
    if name == "PreToolUse" and tool in _SHELL_TOOLS:
        return Event(EventKind.COMMAND, cwd, role, command=str(tool_input.get("command") or ""))
    if name == "PreToolUse" and tool in _EDIT_TOOLS:
        return _edit_event(EventKind.EDIT, payload, cwd)
    if name == "PostToolUse" and tool in _EDIT_TOOLS:
        return _edit_event(EventKind.EDITED, payload, cwd)
    return None


def _reply(name: str, decision: Decision) -> HookReply:
    """A decision in the form Claude Code expects for this hook event."""
    reply: dict[str, Any] = {}
    if name == "PreToolUse" and not decision.allow:
        reply["hookSpecificOutput"] = {
            "hookEventName": name,
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.reason,
        }
    elif not decision.allow:
        reply["decision"] = "block"
        reply["reason"] = decision.reason
    if decision.context:
        reply["hookSpecificOutput"] = {"hookEventName": name, "additionalContext": decision.context}
    if decision.notice:
        reply["systemMessage"] = decision.notice
    return HookReply(stdout=json.dumps(reply, ensure_ascii=True) if reply else "")


class ClaudeCodeAdapter(Adapter):
    """Renders the Claude Code files and answers its hooks."""

    name = NAME
    title = "Claude Code"
    capabilities = Capabilities(skills=True, subagents=True, hooks=True)
    reads = (SETTINGS,)
    local_reads = (LOCAL_SETTINGS,)

    def local_files(
        self, existing: Mapping[str, str | None], folders: Sequence[Path]
    ) -> dict[str, str]:
        if not folders:
            return {}
        return {LOCAL_SETTINGS: merge_local_settings(existing.get(LOCAL_SETTINGS), folders)}

    def files(self, existing: Mapping[str, str | None]) -> dict[str, str]:
        rendered = {
            f".claude/skills/{name}/{assets.SKILL_FILE}": assets.skill(name)
            for name in assets.SKILLS
        }
        rendered.update({f".claude/agents/{name}.md": _agent_file(name) for name in assets.AGENTS})
        rendered[SETTINGS] = merge_settings(existing.get(SETTINGS))
        return rendered

    def hook(
        self, event: str, payload: Mapping[str, Any], cwd: Path, today: datetime.date
    ) -> HookReply:
        where = _path(payload.get("cwd"), cwd) or cwd
        neutral = _event(event, payload, where)
        if neutral is None:
            return HookReply()
        return _reply(event, decide(neutral, today))

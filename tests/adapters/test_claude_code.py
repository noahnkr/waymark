"""The Claude Code adapter: the files it installs, and recorded hook payloads fed to wm hook.

The payloads follow the shapes in the Claude Code hooks reference: the common
fields, ``tool_name`` and ``tool_input`` on tool events, ``agent_type`` when
the hook fires inside a subagent, and ``last_assistant_message`` on
SubagentStop.
"""

import datetime
import io
import json
from pathlib import Path
from typing import Any

import pytest

from tests.support import Workspace
from waymark import adapters, assets
from waymark.adapters.claude_code import (
    LOCAL_SETTINGS,
    NAME,
    SETTINGS,
    merge_local_settings,
    merge_settings,
)
from waymark.cli import EXIT_OK, EXIT_REFUSED, main
from waymark.services import lifecycle

CHANGE = "add-limit"
TASKS_FILE = f"changes/{CHANGE}/tasks.md"
DAY = datetime.date(2026, 1, 15)
SNAPSHOTS = Path(__file__).parent / "snapshots"
HEAD = "# Tasks\n\n## 1. Limit\n\n"


class Hooks:
    """Feeds hook payloads to ``wm hook`` the way the tool does: JSON on standard input."""

    def __init__(
        self,
        project: Workspace,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self.project = project
        self.monkeypatch = monkeypatch
        self.capsys = capsys
        monkeypatch.chdir(project.root)

    def fire(self, event: str, expect: int = EXIT_OK, **fields: Any) -> dict[str, Any]:
        payload = {
            "session_id": "abc123",
            "transcript_path": "/home/user/.claude/projects/p/abc123.jsonl",
            "cwd": str(self.project.root),
            "permission_mode": "default",
            "hook_event_name": event,
            **fields,
        }
        self.monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        code = main(["hook", NAME, event])
        captured = self.capsys.readouterr()
        assert code == expect, captured.out + captured.err
        reply: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
        return reply

    def tool(
        self, name: str, tool_input: dict[str, Any], agent: str | None = None
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {"tool_name": name, "tool_input": tool_input, "tool_use_id": "t1"}
        if agent:
            fields |= {"agent_id": "agent-1", "agent_type": agent}
        return self.fire("PreToolUse", **fields)

    def stop(self, agent: str, message: str, active: bool = False) -> dict[str, Any]:
        return self.fire(
            "SubagentStop",
            stop_hook_active=active,
            agent_id="agent-1",
            agent_type=agent,
            agent_transcript_path="/home/user/.claude/projects/p/abc123/subagents/agent-1.jsonl",
            last_assistant_message=message,
        )


def denied(reply: dict[str, Any]) -> str:
    output = reply["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    reason: str = output["permissionDecisionReason"]
    return reason


@pytest.fixture
def hooks(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Hooks:
    project.change()
    lifecycle.accept(project.root, CHANGE, DAY)
    return Hooks(project, monkeypatch, capsys)


def generated() -> dict[str, str]:
    return adapters.get(NAME).files({})


def test_generated_settings_and_agents_match_their_snapshots() -> None:
    files = generated()
    for path in (SETTINGS, ".claude/agents/wm-implementer.md", ".claude/agents/wm-reviewer.md"):
        snapshot = (SNAPSHOTS / path.rsplit("/", 1)[-1]).read_bytes().decode("utf-8")
        assert files[path] == snapshot.replace("\r\n", "\n"), path


def test_skills_are_copied_unchanged_into_the_tools_folder() -> None:
    files = generated()
    for name in assets.SKILLS:
        assert files[f".claude/skills/{name}/SKILL.md"] == assets.skill(name)
    assert len([path for path in files if "/skills/" in path]) == len(assets.SKILLS) == 8


def test_adapter_declares_its_tools_capabilities() -> None:
    adapter = adapters.get(NAME)
    capabilities = adapter.capabilities
    assert (capabilities.skills, capabilities.subagents, capabilities.hooks) == (True, True, True)
    assert adapter.title == "Claude Code"
    assert adapters.names() == (NAME,)


def test_agent_definitions_keep_the_reviewer_read_only() -> None:
    files = generated()
    reviewer = files[".claude/agents/wm-reviewer.md"]
    assert "disallowedTools: Edit, Write, MultiEdit, NotebookEdit, Agent, SubagentHandback" in (
        reviewer
    )
    implementer = files[".claude/agents/wm-implementer.md"]
    assert "disallowedTools: Agent, SubagentHandback\n" in implementer
    for text in (reviewer, files[".claude/agents/wm-implementer.md"]):
        assert text.startswith("---\nname: wm-")


def test_settings_merge_keeps_everything_that_is_not_wms() -> None:
    theirs: dict[str, Any] = {
        "permissions": {"allow": ["Bash(npm test)"]},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "./lint.sh"}]}
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "./notify.sh"}]}],
        },
    }
    merged = json.loads(merge_settings(json.dumps(theirs)))
    assert merged["permissions"] == theirs["permissions"]
    assert merged["hooks"]["Stop"] == theirs["hooks"]["Stop"]
    assert merged["hooks"]["PreToolUse"][0] == theirs["hooks"]["PreToolUse"][0]
    assert merged["hooks"]["PreToolUse"][1]["hooks"][0]["command"] == f"wm hook {NAME} PreToolUse"
    assert set(merged["hooks"]) == {
        "PreToolUse",
        "Stop",
        "SessionStart",
        "PostToolUse",
        "SubagentStop",
    }


def test_settings_merge_replaces_wms_own_entries_and_is_stable() -> None:
    once = merge_settings(None)
    assert merge_settings(once) == once
    old = once.replace(f"wm hook {NAME} PreToolUse", "wm hook some-old-name BeforeTool")
    assert merge_settings(old) == once
    mixed = json.loads(once)
    mixed["hooks"]["PreToolUse"][0]["hooks"].append({"type": "command", "command": "./mine.sh"})
    again = json.loads(merge_settings(json.dumps(mixed)))
    commands = [h["command"] for group in again["hooks"]["PreToolUse"] for h in group["hooks"]]
    assert commands == ["./mine.sh", f"wm hook {NAME} PreToolUse"]


def test_settings_that_are_not_an_object_are_not_merged() -> None:
    for broken in ("[1, 2]", '{"hooks": []}'):
        with pytest.raises(ValueError, match="not an object"):
            merge_settings(broken)
    with pytest.raises(json.JSONDecodeError):
        merge_settings("{not json")


def test_session_start_adds_the_status_as_context(hooks: Hooks) -> None:
    reply = hooks.fire("SessionStart", source="startup", model="some-model")
    output = reply["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    assert "Changes in flight" in output["additionalContext"]
    assert CHANGE in output["additionalContext"]


def test_starting_an_implementer_with_more_than_change_and_item_is_denied(hooks: Hooks) -> None:
    reply = hooks.tool(
        "Agent",
        {
            "description": "Build the cap",
            "subagent_type": "wm-implementer",
            "prompt": "Implement add-limit 1.1. Remember to use the helper.",
        },
    )
    assert 'exactly "<change> <item>"' in denied(reply)


def test_starting_an_implementer_with_change_and_item_is_allowed(hooks: Hooks) -> None:
    agent = {"description": "Build", "subagent_type": "wm-implementer", "prompt": "add-limit 1.1"}
    assert hooks.tool("Agent", agent) == {}
    other = {"description": "Look", "subagent_type": "Explore", "prompt": "find the search code"}
    assert hooks.tool("Agent", other) == {}


def test_starting_an_implementer_on_an_item_without_criteria_is_denied(hooks: Hooks) -> None:
    reply = hooks.tool("Agent", {"subagent_type": "wm-implementer", "prompt": "add-limit 1.2"})
    assert "has no criteria" in denied(reply)


def test_reviewers_edit_is_denied(hooks: Hooks) -> None:
    path = str(hooks.project.root / "src" / "app.py")
    reply = hooks.tool(
        "Edit", {"file_path": path, "old_string": "a", "new_string": "b"}, "wm-reviewer"
    )
    assert "A reviewer edits nothing" in denied(reply)
    assert hooks.tool("Write", {"file_path": path, "content": "x"}, "wm-implementer") == {}


def test_implementers_edit_of_the_record_is_denied_except_for_notes(hooks: Hooks) -> None:
    tasks = str(hooks.project.path(TASKS_FILE))
    proposal = str(hooks.project.path(f"changes/{CHANGE}/proposal.md"))
    note = {
        "file_path": tasks,
        "old_string": "fifty-one matches\n",
        "new_string": "fifty-one matches\n  - Note: used the existing sorter\n",
    }
    assert hooks.tool("Edit", note, "wm-implementer") == {}
    reply = hooks.tool("Write", {"file_path": proposal, "content": "# x\n"}, "wm-implementer")
    assert "An implementer may add" in denied(reply)


def test_hand_written_evidence_is_denied_for_every_agent(hooks: Hooks) -> None:
    tasks = str(hooks.project.path(TASKS_FILE))
    tick = {"file_path": tasks, "old_string": "- [ ] 1.1", "new_string": "- [x] 1.1"}
    assert "only wm writes evidence" in denied(hooks.tool("Edit", tick))
    several = {
        "file_path": tasks,
        "edits": [
            {"old_string": "Cap the result count", "new_string": "Cap the results"},
            {"old_string": "- [ ] 1.2", "new_string": "- [x] 1.2", "replace_all": False},
        ],
    }
    assert "adds the tick on item 1.2" in denied(hooks.tool("MultiEdit", several))
    harmless = {"file_path": tasks, "old_string": "Cap the result count", "new_string": "Cap it"}
    assert hooks.tool("Edit", harmless) == {}


def test_edit_of_a_living_spec_is_denied(hooks: Hooks) -> None:
    spec = str(hooks.project.path("specs/search.md"))
    assert "Write a delta" in denied(hooks.tool("Write", {"file_path": spec, "content": "# S\n"}))


def test_relative_file_paths_are_read_against_the_hooks_folder(hooks: Hooks) -> None:
    reply = hooks.tool("Write", {"file_path": "waymark/specs/search.md", "content": "# S\n"})
    assert "Write a delta" in denied(reply)


def test_record_file_is_validated_after_each_edit(hooks: Hooks) -> None:
    path = hooks.project.path(f"changes/{CHANGE}/specs/search.md")
    fields: dict[str, Any] = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(path), "old_string": "a", "new_string": "b"},
        "tool_response": {"filePath": str(path)},
    }
    assert hooks.fire("PostToolUse", **fields) == {}
    hooks.project.replace(f"changes/{CHANGE}/specs/search.md", "- WHEN a search runs\n", "")
    reply = hooks.fire("PostToolUse", **fields)
    assert reply["decision"] == "block"
    assert "1 format problem" in reply["reason"]


def test_wm_accept_and_the_archive_override_are_denied_for_every_agent(hooks: Hooks) -> None:
    for agent in (None, "wm-implementer", "wm-reviewer"):
        reply = hooks.tool("Bash", {"command": "wm accept add-limit", "description": "x"}, agent)
        assert "Only the human accepts a change" in denied(reply)
    override = {"command": 'wm archive add-limit --outcome "x" --override "y"'}
    assert "Only the human may archive" in denied(hooks.tool("PowerShell", override))
    assert hooks.tool("Bash", {"command": "wm status"}) == {}


def test_subagents_writing_commands_commits_and_pushes_are_denied(hooks: Hooks) -> None:
    tick = hooks.tool("Bash", {"command": "wm tick add-limit 1.1"}, "wm-implementer")
    assert "writes the record" in denied(tick)
    commit = hooks.tool("Bash", {"command": 'git commit -am "feat: x"'}, "wm-implementer")
    assert "The planner commits" in denied(commit)
    assert hooks.tool("Bash", {"command": "wm tick add-limit 1.1"}) == {}
    assert hooks.tool("Bash", {"command": 'git commit -am "feat: x"'}) == {}


def test_reviewers_state_changing_command_is_denied(hooks: Hooks) -> None:
    reply = hooks.tool("Bash", {"command": "rm -rf build && pytest"}, "wm-reviewer")
    assert "A reviewer runs read-only commands" in denied(reply)
    assert hooks.tool("Bash", {"command": "pytest -q"}, "wm-reviewer") == {}
    assert hooks.tool("Bash", {"command": "rm -rf build"}, "wm-implementer") == {}


def test_implementer_that_stops_without_its_ending_is_kept_running(hooks: Hooks) -> None:
    reply = hooks.stop("wm-implementer", "I finished the work and the tests pass.")
    assert reply["decision"] == "block"
    assert "RESULT: done | partial | spec-gap | blocked" in reply["reason"]
    assert "- [ ] 1.1" in hooks.project.read(TASKS_FILE)


def test_implementers_result_ticks_its_item(hooks: Hooks) -> None:
    reply = hooks.stop("wm-implementer", "Done.\n\nITEM: add-limit 1.1\nRESULT: done: verified")
    assert reply == {"systemMessage": "Waymark: Ticked item 1.1 of add-limit."}
    assert "- [x] 1.1 Cap the result count" in hooks.project.read(TASKS_FILE)


def test_implementers_blocked_result_writes_the_blocked_line(hooks: Hooks) -> None:
    hooks.stop("wm-implementer", "ITEM: add-limit 1.1\nRESULT: blocked: no access to the index")
    assert "  - Blocked: no access to the index" in hooks.project.read(TASKS_FILE)


def test_reviewers_verdict_is_written_as_the_review_record(hooks: Hooks) -> None:
    today = datetime.date.today().isoformat()
    lifecycle.tick(hooks.project.root, CHANGE, "1.1")
    reply = hooks.stop("wm-reviewer", "ITEM: add-limit 1.1\nVERDICT: changes: off by one at fifty")
    assert "Recorded the verdict changes" in reply["systemMessage"]
    line = f"  - (review) {today} changes: off by one at fifty"
    assert line in hooks.project.read(TASKS_FILE)


def test_agent_already_asked_once_is_released_with_a_notice(hooks: Hooks) -> None:
    reply = hooks.stop("wm-implementer", "Still no ending.", active=True)
    assert "decision" not in reply
    assert "recorded nothing for the implementer" in reply["systemMessage"]


def test_other_subagents_stopping_is_ignored(hooks: Hooks) -> None:
    assert hooks.stop("Explore", "Found three files.") == {}
    assert hooks.stop("", "an internal agent") == {}


def test_events_and_tools_wm_does_not_handle_are_ignored(hooks: Hooks) -> None:
    assert hooks.fire("Notification", message="hello") == {}
    assert hooks.tool("Read", {"file_path": str(hooks.project.path(TASKS_FILE))}) == {}
    assert hooks.fire("PostToolUse", tool_name="Bash", tool_input={"command": "ls"}) == {}


def test_hook_outside_a_waymark_project_stays_out_of_the_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = {"cwd": str(tmp_path), "tool_name": "Bash", "tool_input": {"command": "wm accept x"}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert main(["hook", NAME, "PreToolUse"]) == EXIT_OK
    assert capsys.readouterr().out == ""


def test_hook_with_bad_input_or_an_unknown_tool_exits_1_without_blocking(
    hooks: Hooks, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert main(["hook", NAME, "PreToolUse"]) == EXIT_REFUSED
    assert "not JSON" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert main(["hook", "no-such-tool", "PreToolUse"]) == EXIT_REFUSED
    assert "Known tools" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO('{"tool_name": "Edit", "tool_input": "oops"}'))
    assert main(["hook", NAME, "PreToolUse"]) == EXIT_REFUSED
    assert "the hook failed" in capsys.readouterr().err


def test_code_repos_are_attached_through_the_per_machine_settings(tmp_path: Path) -> None:
    api, web = tmp_path / "api", tmp_path / "web"
    existing = json.dumps(
        {"model": "x", "permissions": {"allow": ["Bash(ls)"], "additionalDirectories": [str(api)]}}
    )
    merged = json.loads(merge_local_settings(existing, [api, web]))
    assert merged["model"] == "x"
    assert merged["permissions"]["allow"] == ["Bash(ls)"]
    assert merged["permissions"]["additionalDirectories"] == [str(api), str(web)]


def test_attached_folders_are_never_removed_from_the_per_machine_settings(tmp_path: Path) -> None:
    mine = str(tmp_path / "mine")
    existing = json.dumps({"permissions": {"additionalDirectories": [mine]}})
    merged = json.loads(merge_local_settings(existing, [tmp_path / "api"]))
    assert mine in merged["permissions"]["additionalDirectories"]


@pytest.mark.parametrize(
    "existing", ["[]", '{"permissions": []}', '{"permissions": {"additionalDirectories": "x"}}']
)
def test_per_machine_settings_of_the_wrong_shape_are_refused(existing: str) -> None:
    with pytest.raises(ValueError, match="not"):
        merge_local_settings(existing, [Path("api")])


def test_adapter_writes_no_per_machine_file_without_folders() -> None:
    adapter = adapters.get(NAME)
    assert adapter.local_reads == (LOCAL_SETTINGS,)
    assert adapter.local_files({LOCAL_SETTINGS: None}, []) == {}

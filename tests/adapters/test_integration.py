"""Installing and updating the files Waymark owns, and the stub second adapter."""

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import Workspace
from waymark import __version__, adapters, assets
from waymark.adapters import Adapter, Capabilities
from waymark.cli import build_parser
from waymark.record.project import find_project
from waymark.record.record import load_record
from waymark.services import integration, setup
from waymark.services.common import Refusal
from waymark.services.migrations import Migration

TOOL = adapters.names()[0]
SETTINGS = ".claude/settings.json"


class StubAdapter(Adapter):
    """A second tool, used in tests only: skills in its own folder, no agents, no hooks."""

    name = "stub-tool"
    title = "Stub Tool"
    capabilities = Capabilities(skills=True, subagents=False, hooks=False)

    def files(self, existing: Mapping[str, str | None]) -> dict[str, str]:
        del existing
        return {f".stub/skills/{name}/SKILL.md": assets.skill(name) for name in assets.SKILLS}


@pytest.fixture
def stub() -> Iterator[StubAdapter]:
    adapter = StubAdapter()
    adapters.register(adapter)
    yield adapter
    adapters._REGISTRY.pop(adapter.name)


def files_under(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git/" not in path.as_posix()
    }


@pytest.fixture
def initialized(tmp_path: Path) -> Path:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    return tmp_path


def test_init_installs_the_skills_agents_and_hooks(initialized: Path) -> None:
    files = files_under(initialized)
    for name in assets.SKILLS:
        shared = files[f".agents/skills/{name}/SKILL.md"]
        assert shared == assets.skill(name).encode("utf-8")
        assert files[f".claude/skills/{name}/SKILL.md"] == shared
    assert ".claude/agents/wm-implementer.md" in files
    assert ".claude/agents/wm-reviewer.md" in files
    hooks = json.loads(files[SETTINGS])["hooks"]
    assert set(hooks) == {"SessionStart", "PreToolUse", "PostToolUse", "SubagentStop"}
    record = load_record(find_project(initialized))
    assert record.problems == ()
    assert record.config is not None
    assert record.config.agent_tools == (TOOL,)


def test_skills_are_copied_not_linked(initialized: Path) -> None:
    for path in sorted(initialized.rglob("SKILL.md")):
        assert path.is_file()
        assert not path.is_symlink()
    assert len(list(initialized.rglob("SKILL.md"))) == 2 * len(assets.SKILLS)


def test_init_keeps_the_settings_the_project_already_has(tmp_path: Path) -> None:
    git_init(tmp_path)
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text('{"permissions": {"allow": ["Bash(make test)"]}}', encoding="utf-8")
    (tmp_path / ".claude" / "skills" / "deploy").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "deploy" / "SKILL.md").write_text("mine\n", encoding="utf-8")
    setup.init_project(tmp_path)
    merged = json.loads(settings.read_text(encoding="utf-8"))
    assert merged["permissions"] == {"allow": ["Bash(make test)"]}
    assert "SessionStart" in merged["hooks"]
    assert (tmp_path / ".claude/skills/deploy/SKILL.md").read_text(encoding="utf-8") == "mine\n"


def test_init_refuses_settings_it_cannot_read_and_writes_nothing(tmp_path: Path) -> None:
    git_init(tmp_path)
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("{not json", encoding="utf-8")
    with pytest.raises(Refusal, match="can't be read as settings"):
        setup.init_project(tmp_path)
    assert not (tmp_path / "waymark").exists()
    assert not (tmp_path / ".agents").exists()
    assert settings.read_text(encoding="utf-8") == "{not json"


def test_init_refuses_a_tool_it_does_not_know(tmp_path: Path) -> None:
    git_init(tmp_path)
    with pytest.raises(Refusal, match="Known tools"):
        setup.init_project(tmp_path, tools=("no-such-tool",))
    assert not (tmp_path / "waymark").exists()


def test_update_on_a_current_project_changes_nothing(initialized: Path) -> None:
    before = files_under(initialized)
    done = integration.update(initialized)
    assert done.message == "Everything is up to date."
    assert done.paths == ()
    assert files_under(initialized) == before


def test_update_regenerates_only_the_files_waymark_owns(initialized: Path) -> None:
    skill = initialized / ".claude/skills/wm-apply/SKILL.md"
    skill.write_text("edited by hand\n", encoding="utf-8")
    (initialized / ".agents/skills/wm-pr/SKILL.md").unlink()
    mine = initialized / ".claude/skills/deploy/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("mine\n", encoding="utf-8")
    notes = initialized / ".claude/agents/notes.md"
    notes.write_text("my own agent\n", encoding="utf-8")
    settings = initialized / SETTINGS
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["model"] = "some-model"
    data["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "./notify.sh"}]}]
    del data["hooks"]["SubagentStop"]
    settings.write_text(json.dumps(data), encoding="utf-8")

    done = integration.update(initialized)
    assert set(done.paths) == {
        ".agents/skills/wm-pr/SKILL.md",
        ".claude/skills/wm-apply/SKILL.md",
        SETTINGS,
    }
    assert "created: .agents/skills/wm-pr/SKILL.md" in done.message
    assert "updated: .claude/skills/wm-apply/SKILL.md" in done.message
    assert "Review the changes and commit them." in done.message
    assert skill.read_text(encoding="utf-8") == assets.skill("wm-apply")
    assert mine.read_text(encoding="utf-8") == "mine\n"
    assert notes.read_text(encoding="utf-8") == "my own agent\n"
    merged = json.loads(settings.read_text(encoding="utf-8"))
    assert merged["model"] == "some-model"
    assert merged["hooks"]["Stop"] == data["hooks"]["Stop"]
    assert "SubagentStop" in merged["hooks"]


def test_update_is_refused_when_the_pinned_version_differs(initialized: Path) -> None:
    config = initialized / "waymark/config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(text.replace(f'"{__version__}"', '"9.9.9"'), encoding="utf-8")
    (initialized / ".claude/skills/wm-apply/SKILL.md").write_text("old\n", encoding="utf-8")
    with pytest.raises(Refusal, match=r"waymark-cli==9\.9\.9"):
        integration.update(initialized)
    assert (initialized / ".claude/skills/wm-apply/SKILL.md").read_text(encoding="utf-8") == "old\n"


def test_update_migrates_the_record_before_regenerating(
    initialized: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mark(files: object, transaction: object) -> None:
        del files
        transaction.write("charter.md", "# Migrated\n")  # type: ignore[attr-defined]

    monkeypatch.setattr("waymark.services.migrations.MIGRATIONS", (Migration(1, "mark it", mark),))
    monkeypatch.setattr("waymark.services.migrations.RECORD_FORMAT", 2)
    monkeypatch.setattr(
        "waymark.services.migrations.migrate.__defaults__", ((Migration(1, "mark it", mark),), 2)
    )
    monkeypatch.setattr("waymark.record.config.RECORD_FORMAT", 2)
    monkeypatch.setattr("waymark.services.common.RECORD_FORMAT", 2)
    with pytest.raises(Refusal, match="wm update"):
        setup.create_change(initialized, "add-limit")
    done = integration.update(initialized)
    assert "Migrated the record: format 1 to 2: mark it." in done.message
    assert (initialized / "waymark/charter.md").read_text(encoding="utf-8") == "# Migrated\n"
    assert "record_format = 2" in (initialized / "waymark/config.toml").read_text(encoding="utf-8")
    setup.create_change(initialized, "add-limit")


def test_update_refuses_a_tool_the_settings_name_but_wm_does_not_know(initialized: Path) -> None:
    config = initialized / "waymark/config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(text.replace(f'"{TOOL}"', '"no-such-tool"'), encoding="utf-8")
    with pytest.raises(Refusal, match='"no-such-tool" is not an agent tool wm knows'):
        integration.update(initialized)


def test_stub_second_adapter_installs_the_skills_with_no_core_change(
    tmp_path: Path, stub: StubAdapter
) -> None:
    git_init(tmp_path)
    done = setup.init_project(tmp_path, tools=(stub.name,))
    assert "Stub Tool" in done.message
    files = files_under(tmp_path)
    for name in assets.SKILLS:
        expected = assets.skill(name).encode("utf-8")
        assert files[f".agents/skills/{name}/SKILL.md"] == expected
        assert files[f".stub/skills/{name}/SKILL.md"] == expected
    assert not any(path.startswith(".claude/") for path in files)
    record = load_record(find_project(tmp_path))
    assert record.problems == ()
    assert record.config is not None
    assert record.config.agent_tools == ("stub-tool",)
    assert integration.update(tmp_path).message == "Everything is up to date."


def test_two_tools_can_be_installed_side_by_side(tmp_path: Path, stub: StubAdapter) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path, tools=(TOOL, stub.name))
    files = files_under(tmp_path)
    assert ".stub/skills/wm-apply/SKILL.md" in files
    assert ".claude/skills/wm-apply/SKILL.md" in files
    assert len([path for path in files if path.startswith(".agents/skills/")]) == len(assets.SKILLS)


def test_tool_without_hooks_answers_no_hook(stub: StubAdapter, workspace: Workspace) -> None:
    import datetime  # noqa: PLC0415 - only this test needs a date

    reply = stub.hook("AnyEvent", {"tool_name": "Bash"}, workspace.root, datetime.date(2026, 1, 1))
    assert (reply.stdout, reply.stderr, reply.code) == ("", "", 0)
    assert not stub.capabilities.hooks


def all_asset_texts() -> dict[str, str]:
    texts = {f"skill {name}": assets.skill(name) for name in assets.SKILLS}
    texts.update({f"agent {name}": "\n".join(assets.agent(name)) for name in assets.AGENTS})
    return texts


def test_skills_and_agents_are_tool_neutral() -> None:
    tool_words = [name.split("-")[0] for name in adapters.names()] + ["anthropic"]
    for label, text in all_asset_texts().items():
        lowered = text.casefold()
        for word in tool_words:
            assert word not in lowered, f"{label} names a tool: {word}"
        assert ".claude" not in lowered, label


def test_skills_have_the_standard_header_and_a_plain_description() -> None:
    for name in assets.SKILLS:
        text = assets.skill(name)
        header = text.split("---\n")[1]
        fields = dict(line.split(": ", 1) for line in header.strip().split("\n"))
        assert set(fields) == {"name", "description"}
        assert fields["name"] == name
        assert ": " not in fields["description"], name
        assert " #" not in fields["description"], name
        assert len(fields["description"]) < 400, name
    for name in assets.AGENTS:
        description, body = assets.agent(name)
        assert ": " not in description, name
        assert body.startswith("You are ")


def test_skills_and_agents_name_only_commands_that_exist() -> None:
    parser = build_parser()
    subparsers = next(a for a in parser._actions if a.dest == "==SUPPRESS==" and a.choices)
    known = set(subparsers.choices or ())
    for label, text in all_asset_texts().items():
        used = set(re.findall(r"`wm ([a-z]+)\b", text))
        assert used <= known, f"{label} names unknown commands: {sorted(used - known)}"
        skills = set(re.findall(r"`(wm-[a-z]+)`", text))
        assert skills <= set(assets.SKILLS) | set(assets.AGENTS), label


def test_delegated_agents_are_told_how_to_end() -> None:
    _, implementer = assets.agent(assets.IMPLEMENTER)
    _, reviewer = assets.agent(assets.REVIEWER)
    assert "ITEM: <change> <item>\nRESULT: <done | partial | spec-gap | blocked>" in implementer
    assert "ITEM: <change> <item>\nVERDICT: <pass | changes | spec-gap>" in reviewer
    assert "wm context <change> <item> --for implement" in implementer
    assert "wm context <change> <item> --for review" in reviewer

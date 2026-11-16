"""The maintainer skills: kept in tools/skills/, installed per machine into each tool's folder."""

import subprocess
from pathlib import Path

from tools import install_skills

NAMES = ["waymark-check-docs", "waymark-draft-docs", "waymark-release", "waymark-write-docs"]


def test_the_maintainer_skills_live_in_tools_skills() -> None:
    assert [path.name for path in install_skills.maintainer_skills()] == NAMES


def test_install_copies_each_skill_into_the_tool_folder(tmp_path: Path) -> None:
    mine = tmp_path / ".claude/skills/my-own/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("mine\n", encoding="utf-8")
    report = install_skills.install(tmp_path)
    assert report == [f"created: .claude/skills/{name}" for name in NAMES]
    for name in NAMES:
        installed = tmp_path / ".claude/skills" / name / "SKILL.md"
        source = install_skills.SOURCE / name / "SKILL.md"
        assert installed.read_bytes() == source.read_bytes()
    assert mine.read_text(encoding="utf-8") == "mine\n"


def test_install_again_replaces_a_stale_copy(tmp_path: Path) -> None:
    install_skills.install(tmp_path)
    stale = tmp_path / ".claude/skills/waymark-release/old.md"
    stale.write_text("old\n", encoding="utf-8")
    report = install_skills.install(tmp_path)
    assert report[2] == "updated: .claude/skills/waymark-release"
    assert not stale.exists()


def test_nothing_in_an_agent_tool_folder_is_committed() -> None:
    """Charter constraint 7: everything in an agent tool folder is per machine."""
    tracked = subprocess.run(
        ["git", "-C", str(install_skills.ROOT), "ls-files", "--", ".agents", ".claude"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert tracked == []

"""The doctors: what they check, how each check comes out, and that they change nothing."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace
from tests.views.validator import errors
from waymark import __version__
from waymark.services import setup
from waymark.services.atlas import point, register
from waymark.services.doctor import Report, Status, atlas_doctor, doctor
from waymark.views import payloads, render
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

TOOL_ATLAS = ATLAS_CONFIG.replace('"some-tool"', '"claude-code"')


def outcome(report: Report) -> dict[str, Status]:
    return {check.name: check.status for check in report.checks}


def message(report: Report, name: str) -> str:
    return next(check.message for check in report.checks if check.name == name)


def snapshot(*roots: Path) -> dict[str, bytes]:
    """Every file under some folders, so a test can tell that nothing changed."""
    files: dict[str, bytes] = {}
    for root in roots:
        for folder, _, names in os.walk(root):
            for name in names:
                path = Path(folder) / name
                files[str(path)] = path.read_bytes()
    return files


@pytest.fixture
def on_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: str(tmp_path / "bin" / "wm"))


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    return atlas


def test_doctor_reports_wm_missing_from_path_as_an_error(
    project: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    report = doctor(project.root)
    assert outcome(report)["wm on PATH"] is Status.ERROR
    assert "pipx install" in message(report, "wm on PATH")
    assert report.failed


@pytest.mark.usefixtures("on_path")
def test_doctor_without_a_project_says_how_to_find_one(tmp_path: Path) -> None:
    report = doctor(tmp_path)
    assert outcome(report)["project"] is Status.ERROR
    assert "No Waymark project found" in message(report, "project")


@pytest.mark.usefixtures("on_path")
def test_doctor_reports_a_different_version_pin_as_an_error(project: Workspace) -> None:
    project.write("config.toml", CONFIG.replace(__version__, "9.9.9"))
    report = doctor(project.root)
    assert outcome(report)["version pin"] is Status.ERROR
    assert "waymark-cli==9.9.9" in message(report, "version pin")


@pytest.mark.usefixtures("on_path")
def test_doctor_warns_when_the_agent_tool_files_are_out_of_date(suite: Workspace) -> None:
    """Scenario: Agent files out of date."""
    report = doctor(suite.root)
    assert outcome(report)["agent tool files"] is Status.WARNING
    assert 'Run "wm init"' in message(report, "agent tool files")
    assert "commit" not in message(report, "agent tool files")
    assert outcome(report)["atlas"] is Status.OK
    assert not report.failed


@pytest.mark.usefixtures("on_path")
def test_doctor_warns_about_a_reference_not_on_this_machine(tmp_path: Path) -> None:
    shop = Workspace(tmp_path / "shop", CONFIG + "\n[references.billing]\n")
    git_init(shop.root)
    report = doctor(shop.root)
    assert outcome(report)["reference billing"] is Status.WARNING


def test_atlas_doctor_checks_registry_repos_branches_and_pins(suite: Workspace) -> None:
    before = outcome(atlas_doctor(suite.root))
    assert before["atlas registered"] is Status.WARNING
    assert before["repo api"] is Status.WARNING
    assert before["repo web"] is Status.WARNING
    register(suite.root)
    report = atlas_doctor(suite.root)
    doctor_outcome = outcome(report)
    assert doctor_outcome["atlas registered"] is Status.OK
    assert doctor_outcome["repo api"] is Status.OK
    assert "on branch" in message(report, "repo api")
    assert doctor_outcome["attached repos"] is Status.OK
    assert doctor_outcome["version pin"] is Status.OK
    assert not report.failed


def test_atlas_doctor_warns_about_a_pointer_with_another_pin(
    suite: Workspace, tmp_path: Path
) -> None:
    register(suite.root)
    point(tmp_path / "suite-api", "suite")
    assert outcome(atlas_doctor(suite.root))["pointer api"] is Status.OK
    pointer = tmp_path / "suite-api" / "waymark" / "config.toml"
    pointer.write_text(
        pointer.read_text(encoding="utf-8").replace(__version__, "0.0.1"), encoding="utf-8"
    )
    report = atlas_doctor(suite.root)
    assert outcome(report)["pointer api"] is Status.WARNING
    assert "wm atlas point suite" in message(report, "pointer api")


def test_atlas_doctor_warns_about_registry_entries_the_settings_dont_list(
    suite: Workspace, tmp_path: Path, isolated_registry: Path
) -> None:
    register(suite.root)
    git_init(tmp_path / "old")
    text = isolated_registry.read_text(encoding="utf-8")
    old = json.dumps(str(tmp_path / "old"))
    isolated_registry.write_text(
        text + f'\n[atlases."suite".repos."old"]\npath = {old}\n', encoding="utf-8"
    )
    assert outcome(atlas_doctor(suite.root))["repo old"] is Status.WARNING


def test_atlas_doctor_outside_an_atlas_is_an_error(project: Workspace) -> None:
    report = atlas_doctor(project.root)
    assert outcome(report) == {"atlas": Status.ERROR}
    assert report.failed


@pytest.mark.usefixtures("on_path")
def test_doctors_change_nothing(suite: Workspace, tmp_path: Path, isolated_registry: Path) -> None:
    before = snapshot(tmp_path)
    doctor(suite.root)
    atlas_doctor(suite.root)
    assert snapshot(tmp_path) == before
    assert not isolated_registry.exists()


@pytest.mark.usefixtures("on_path")
def test_doctor_payload_keeps_folders_out_of_its_json(suite: Workspace) -> None:
    payload = payloads.doctor(atlas_doctor(suite.root))
    assert errors(render.public(payload), SCHEMAS["doctor"]) == []
    text = render.to_text(payload, Style())
    assert str(suite.root) in text
    assert "Nothing was changed." in text
    assert json.dumps(str(suite.root))[1:-1] not in render.to_json(payload)


@pytest.mark.usefixtures("on_path")
def test_doctor_json_names_no_folder_whatever_it_finds(
    tmp_path: Path, isolated_registry: Path
) -> None:
    """Hints, stale entries, missing repos and missing projects all report without a path."""
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS + '\n[references.billing]\npath = "../b"\n')
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    billing = Workspace(tmp_path / "b", CONFIG + '\n[atlas]\nname = "billing"\n')
    git_init(billing.root)
    gone = json.dumps(str(tmp_path / "gone"))
    isolated_registry.write_text(
        f'[atlases."suite"]\npath = {gone}\n\n[atlases."suite".repos."web"]\npath = {gone}\n',
        encoding="utf-8",
    )
    escaped = json.dumps(str(tmp_path))[1:-1]
    for report in (
        doctor(atlas.root),
        atlas_doctor(atlas.root),
        doctor(tmp_path),
        atlas_doctor(tmp_path),
    ):
        text = render.to_json(payloads.doctor(report))
        assert escaped not in text, text


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8")


def committed_project(root: Path, *forced: str) -> None:
    """A project set up by wm init and committed, with some ignored paths added anyway."""
    git_init(root)
    git(root, "config", "user.email", "sam@example.com")
    setup.init_project(root)
    git(root, "add", "-A")
    if forced:
        git(root, "add", "--force", "--", *forced)
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "chore: start")


@pytest.mark.usefixtures("on_path")
def test_scenario_agent_files_committed(tmp_path: Path) -> None:
    """Scenario: Agent files committed."""
    committed_project(tmp_path, ".claude", ".agents")
    tracked = git(tmp_path, "ls-files", "--", ".claude", ".agents").split()
    report = doctor(tmp_path)
    assert outcome(report)["machine files in git"] is Status.WARNING
    text = message(report, "machine files in git")
    assert text.startswith(f"{len(tracked)} file(s) wm writes for each machine are tracked")
    assert f"starting with {sorted(tracked)[0]}." in text
    assert text.count("git rm -r --cached") == 1
    command = text.split("git rm -r --cached ", 1)[1]
    assert command == (
        '".agents/skills/wm-*" ".claude/skills/wm-*" ".claude/agents/wm-*.md" .claude/settings.json'
    )
    assert ".waymark" not in text
    assert not report.failed


@pytest.mark.usefixtures("on_path")
def test_doctor_command_stops_tracking_every_machine_file_and_keeps_them(tmp_path: Path) -> None:
    committed_project(tmp_path, ".claude")
    text = message(doctor(tmp_path), "machine files in git")
    arguments = [part.strip('"') for part in text.split("git rm -r --cached ", 1)[1].split()]
    assert arguments == [
        ".claude/skills/wm-*",
        ".claude/agents/wm-*.md",
        ".claude/settings.json",
    ]
    git(tmp_path, "rm", "-r", "--cached", "--quiet", "--", *arguments)
    assert (tmp_path / ".claude" / "settings.json").is_file()
    git(tmp_path, "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "chore: untrack")
    assert outcome(doctor(tmp_path))["machine files in git"] is Status.OK


@pytest.mark.usefixtures("on_path")
def test_scenario_nothing_tracked(tmp_path: Path) -> None:
    """Scenario: Nothing tracked."""
    committed_project(tmp_path)
    report = doctor(tmp_path)
    assert outcome(report)["machine files in git"] is Status.OK
    assert outcome(report)["agent tool files"] is Status.OK


@pytest.mark.usefixtures("on_path")
def test_doctor_payload_with_tracked_machine_files_validates(tmp_path: Path) -> None:
    committed_project(tmp_path, ".claude")
    payload = payloads.doctor(doctor(tmp_path))
    assert errors(render.public(payload), SCHEMAS["doctor"]) == []


@pytest.mark.usefixtures("on_path")
def test_doctor_has_no_git_hooks_check(tmp_path: Path) -> None:
    committed_project(tmp_path)
    names = [check.name for check in doctor(tmp_path).checks]
    assert not any("hooks" in name for name in names), names
    assert all("git-hooks" not in check.message for check in doctor(tmp_path).checks)

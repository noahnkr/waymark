"""Atlases on this machine: register, point, attach the code repos, read references."""

import json
import subprocess
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace, spec
from waymark import __version__
from waymark.record.registry import load_registry
from waymark.services import integration, setup
from waymark.services.atlas import point, register
from waymark.services.common import Refusal, take_notices
from waymark.services.context import context_pack
from waymark.services.references import reference_record

LOCAL = ".claude/settings.local.json"
TOOL_ATLAS = ATLAS_CONFIG.replace('"some-tool"', '"claude-code"')


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    """An atlas whose "api" repo sits beside it, as its path hint says; "web" has no hint."""
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    return atlas


def local_settings(root: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((root / LOCAL).read_text(encoding="utf-8"))
    return loaded


def ignored(root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", relative], capture_output=True, check=False
    )
    return result.returncode == 0


def test_register_records_the_atlas_and_the_repos_its_hints_lead_to(
    suite: Workspace, tmp_path: Path, isolated_registry: Path
) -> None:
    done = register(suite.root)
    registry = load_registry(isolated_registry)
    assert registry.atlases["suite"].path == suite.root.resolve()
    assert registry.repo("suite", "api") == (tmp_path / "suite-api").resolve()
    assert registry.repo("suite", "web") is None
    assert 'Registered the code repo "api"' in done.message
    assert "wm atlas register web <folder>" in done.message


def test_register_records_one_repo_at_the_folder_given(
    suite: Workspace, tmp_path: Path, isolated_registry: Path
) -> None:
    git_init(tmp_path / "frontend")
    register(suite.root, "web", "../frontend")
    frontend = (tmp_path / "frontend").resolve()
    assert load_registry(isolated_registry).repo("suite", "web") == frontend


def test_register_refuses_a_repo_the_settings_dont_list_or_a_folder_that_isnt_one(
    suite: Workspace, tmp_path: Path
) -> None:
    with pytest.raises(Refusal, match='no code repo "mobile"'):
        register(suite.root, "mobile", "../suite-api")
    (tmp_path / "plain").mkdir()
    with pytest.raises(Refusal, match="not the top folder of a git repository"):
        register(suite.root, "web", "../plain")


def test_register_is_refused_outside_an_atlas(project: Workspace) -> None:
    with pytest.raises(Refusal, match="not in an atlas"):
        register(project.root)


def test_register_is_refused_when_the_registry_cant_be_read(
    suite: Workspace, isolated_registry: Path
) -> None:
    isolated_registry.write_text("[atlases.suite\n", encoding="utf-8")
    with pytest.raises(Refusal, match="can't be read"):
        register(suite.root)
    assert isolated_registry.read_text(encoding="utf-8") == "[atlases.suite\n"


def test_register_attaches_the_code_repos_to_sessions_in_a_per_machine_file(
    tmp_path: Path,
) -> None:
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    (atlas.root / ".claude").mkdir()
    (atlas.root / LOCAL).write_text('{"permissions": {"allow": ["Bash(ls)"]}}', encoding="utf-8")
    register(atlas.root)
    settings = local_settings(atlas.root)
    assert settings["permissions"] == {
        "allow": ["Bash(ls)"],
        "additionalDirectories": [str((tmp_path / "suite-api").resolve())],
    }
    assert ignored(atlas.root, LOCAL)
    register(atlas.root)
    assert local_settings(atlas.root) == settings


def test_update_attaches_the_code_repos_found_on_this_machine(tmp_path: Path) -> None:
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    done = integration.update(atlas.root)
    assert f"created: {LOCAL}" in done.message
    directories = local_settings(atlas.root)["permissions"]
    assert directories == {"additionalDirectories": [str((tmp_path / "suite-api").resolve())]}
    assert ignored(atlas.root, LOCAL)


def test_unreadable_local_settings_are_refused_and_nothing_is_written(
    tmp_path: Path, isolated_registry: Path
) -> None:
    atlas = Workspace(tmp_path / "atlas", TOOL_ATLAS)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    (atlas.root / ".claude").mkdir()
    (atlas.root / LOCAL).write_text("{not json", encoding="utf-8")
    with pytest.raises(Refusal, match="can't be read as settings"):
        register(atlas.root)
    assert not isolated_registry.exists()


def test_init_of_an_atlas_registers_it(tmp_path: Path, isolated_registry: Path) -> None:
    git_init(tmp_path / "atlas")
    done = setup.init_project(tmp_path / "atlas", "suite", ())
    assert 'Registered the atlas "suite"' in done.message
    assert load_registry(isolated_registry).atlases["suite"].path == tmp_path / "atlas"


def test_point_writes_the_pointer_with_a_relative_hint_and_the_atlas_pin(
    suite: Workspace, tmp_path: Path
) -> None:
    register(suite.root)
    done = point(tmp_path / "suite-api", "suite")
    assert "Wrote .waymark/atlas.toml" in done.message
    text = (tmp_path / "suite-api" / ".waymark" / "atlas.toml").read_text(encoding="utf-8")
    assert 'atlas = "suite"\npath = "../atlas"\n' in text
    assert f'wm_version = "{__version__}"' in text
    assert "Updated" in point(tmp_path / "suite-api", "suite", "../atlas").message


def test_point_is_refused_where_it_cant_lead_anywhere(
    suite: Workspace, tmp_path: Path, project: Workspace
) -> None:
    with pytest.raises(Refusal, match="not on this machine's registry"):
        point(tmp_path / "suite-api", "suite")
    with pytest.raises(Refusal, match='not the top folder of the atlas "suite"'):
        point(tmp_path / "suite-api", "suite", "../elsewhere")
    with pytest.raises(Refusal, match="holds a Waymark record itself"):
        point(project.root, "suite", "../atlas")
    with pytest.raises(Refusal, match="not in a git repository"):
        point(tmp_path, "suite", "atlas")


def test_reference_reads_another_atlas_where_it_sits(tmp_path: Path) -> None:
    billing = Workspace(tmp_path / "billing", CONFIG + '\n[atlas]\nname = "billing"\n')
    billing.write("specs/invoices.md", spec(title="Invoices", purpose="How invoices work."))
    project = Workspace(tmp_path / "shop", CONFIG + '\n[references.billing]\npath = "../billing"\n')
    other = reference_record(project.record(), "billing")
    assert list(other.specs) == ["invoices"]
    assert any("wm atlas register" in note for note in take_notices())
    explore = context_pack(project.record(), "explore")
    assert explore["references"] == [
        {
            "atlas": "billing",
            "found": True,
            "specs": [{"name": "invoices", "title": "Invoices", "purpose": "How invoices work."}],
        }
    ]
    assert billing.read("specs/invoices.md") == spec(title="Invoices", purpose="How invoices work.")


def test_reference_to_an_atlas_not_named_or_not_here_is_refused(tmp_path: Path) -> None:
    project = Workspace(tmp_path / "shop", CONFIG + '\n[references.billing]\npath = "../gone"\n')
    with pytest.raises(Refusal, match='references no atlas "auth"'):
        reference_record(project.record(), "auth")
    with pytest.raises(Refusal, match="not on this machine's registry"):
        reference_record(project.record(), "billing")
    assert context_pack(project.record(), "explore")["references"] == [
        {"atlas": "billing", "found": False, "specs": []}
    ]

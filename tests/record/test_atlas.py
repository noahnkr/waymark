"""Finding an atlas and its code repos on this machine, and the project from a code repo."""

from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, Workspace
from waymark.record.atlas import Found, locate_atlas, locate_repo
from waymark.record.config import CodeRepo
from waymark.record.pointer import Pointer, parse_pointer, render_pointer
from waymark.record.project import ProjectNotFoundError, find_project
from waymark.record.registry import Registry

API = CodeRepo("api", "../suite-api")


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    return atlas


def empty(tmp_path: Path) -> Registry:
    return Registry(tmp_path / "registry.toml")


def write_pointer(folder: Path, text: str) -> None:
    (folder / ".waymark").mkdir(parents=True, exist_ok=True)
    (folder / ".waymark" / "atlas.toml").write_bytes(text.encode("utf-8"))


def test_pointer_names_the_atlas_its_hint_and_the_pin() -> None:
    pointer = Pointer("suite", "../atlas", "0.1.0")
    assert parse_pointer(render_pointer(pointer)) == (pointer, None)
    assert parse_pointer('atlas = "suite"\n') == (Pointer("suite", None, None), None)


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("atlas = \n", "not valid TOML"),
        ('path = "../atlas"\n', "names no atlas"),
        ('atlas = "suite"\nrepo = "api"\n', 'holds "repo"'),
        ("atlas = 3\n", "not a string"),
    ],
)
def test_pointer_that_cant_be_read_says_why(text: str, problem: str) -> None:
    pointer, reason = parse_pointer(text)
    assert pointer is None
    assert reason is not None
    assert problem in reason


def test_repo_is_found_through_the_registry_first(suite: Workspace, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere" / "api"
    git_init(elsewhere)
    git_init(tmp_path / "suite-api")
    registry = empty(tmp_path).with_repo("suite", "api", elsewhere)
    location = locate_repo("suite", suite.root, API, registry)
    assert (location.found, location.folder) == (Found.REGISTRY, elsewhere)


def test_repo_hint_is_used_when_it_leads_to_a_git_repository_top(
    suite: Workspace, tmp_path: Path
) -> None:
    git_init(tmp_path / "suite-api")
    location = locate_repo("suite", suite.root, API, empty(tmp_path))
    assert location.found is Found.HINT
    assert location.folder == (tmp_path / "suite-api").resolve()
    assert "wm atlas register" in location.detail


def test_repo_hint_is_not_used_when_it_leads_to_a_plain_folder(
    suite: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "suite-api").mkdir()
    location = locate_repo("suite", suite.root, API, empty(tmp_path))
    assert (location.found, location.folder) == (Found.MISSING, None)
    assert "wm atlas register api <folder>" in location.detail


def test_repo_hint_is_not_used_when_its_pointer_names_another_atlas(
    suite: Workspace, tmp_path: Path
) -> None:
    git_init(tmp_path / "suite-api")
    write_pointer(tmp_path / "suite-api", 'atlas = "other"\n')
    assert locate_repo("suite", suite.root, API, empty(tmp_path)).found is Found.MISSING


def test_stale_registry_entry_falls_back_to_the_hint(suite: Workspace, tmp_path: Path) -> None:
    git_init(tmp_path / "suite-api")
    registry = empty(tmp_path).with_repo("suite", "api", tmp_path / "gone")
    location = locate_repo("suite", suite.root, API, registry)
    assert location.found is Found.HINT
    missing = locate_repo("suite", suite.root, CodeRepo("web", None), registry)
    assert missing.found is Found.MISSING


def test_atlas_is_found_only_where_its_settings_carry_its_name(
    suite: Workspace, tmp_path: Path
) -> None:
    registry = empty(tmp_path).with_atlas("suite", suite.root)
    assert locate_atlas("suite", registry).found is Found.REGISTRY
    assert locate_atlas("other", registry.with_atlas("other", suite.root)).found is Found.MISSING
    hinted = locate_atlas("suite", empty(tmp_path), tmp_path / "suite-api", "../atlas")
    assert (hinted.found, hinted.folder) == (Found.HINT, suite.root.resolve())


def test_project_is_found_from_a_code_repo_through_its_pointer(
    suite: Workspace, tmp_path: Path
) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    write_pointer(code, 'atlas = "suite"\npath = "../atlas"\n')
    (code / "src").mkdir()
    project = find_project(code / "src", empty(tmp_path))
    assert project.root == suite.root.resolve()
    assert project.code_repo == code.resolve()
    assert any("wm atlas register" in note for note in project.notes)


def test_project_is_found_from_a_registered_code_repo_without_a_pointer(
    suite: Workspace, tmp_path: Path
) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    registry = empty(tmp_path).with_atlas("suite", suite.root).with_repo("suite", "api", code)
    project = find_project(code, registry)
    assert (project.root, project.code_repo, project.notes) == (suite.root, code, ())


def test_code_repo_of_several_atlases_needs_a_pointer(suite: Workspace, tmp_path: Path) -> None:
    code = tmp_path / "shared"
    git_init(code)
    registry = (
        empty(tmp_path)
        .with_atlas("suite", suite.root)
        .with_repo("suite", "api", code)
        .with_repo("other", "api", code)
    )
    with pytest.raises(ProjectNotFoundError, match=r"several atlases.*wm atlas point"):
        find_project(code, registry)


def test_pointer_to_an_atlas_not_on_this_machine_says_how_to_get_it(tmp_path: Path) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    write_pointer(code, 'atlas = "suite"\npath = "../atlas"\n')
    with pytest.raises(ProjectNotFoundError, match=r'points to the atlas "suite".*Clone it'):
        find_project(code, empty(tmp_path))

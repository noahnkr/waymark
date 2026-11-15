"""Finding an atlas and its code repos on this machine, and the project from a code repo."""

from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace
from waymark.record.atlas import Found, locate_atlas, locate_repo
from waymark.record.config import CodeRepo
from waymark.record.pointer import Pointer, is_pointer, parse_pointer, render_pointer
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


def write_old_pointer(folder: Path, text: str) -> None:
    (folder / ".waymark").mkdir(parents=True, exist_ok=True)
    (folder / ".waymark" / "atlas.toml").write_bytes(text.encode("utf-8"))


def write_pointer(folder: Path, text: str) -> None:
    (folder / "waymark").mkdir(parents=True, exist_ok=True)
    (folder / "waymark" / "config.toml").write_bytes(text.encode("utf-8"))


def test_pointer_names_the_atlas_its_hint_and_the_pin() -> None:
    pointer = Pointer("suite", "../atlas", "0.1.0")
    text = render_pointer(pointer)
    assert text.startswith("# A pointer, not a record")
    assert "\n[pointer]\n" in text
    assert is_pointer(text)
    assert parse_pointer(text) == (pointer, None)
    assert parse_pointer('[pointer]\natlas = "suite"\n') == (Pointer("suite", None, None), None)


def test_old_pointer_is_still_read() -> None:
    pointer = Pointer("suite", "../atlas", "0.1.0")
    text = render_pointer(pointer, old=True)
    assert "[pointer]" not in text
    assert parse_pointer(text, old=True) == (pointer, None)
    assert parse_pointer('atlas = "suite"\n', old=True) == (Pointer("suite", None, None), None)


@pytest.mark.parametrize(
    ("text", "pointer"),
    [
        ('[pointer]\natlas = "suite"\n', True),
        ("[pointer]\n", True),
        (CONFIG, False),
        (ATLAS_CONFIG, False),
        ('atlas = "suite"\n', False),
        ('pointer = "suite"\n', False),
        ("[pointer\n", False),
    ],
)
def test_pointer_is_told_from_a_records_settings(text: str, pointer: bool) -> None:
    assert is_pointer(text) is pointer


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("[pointer]\natlas = \n", "waymark/config.toml is not valid TOML"),
        ('[pointer]\npath = "../atlas"\n', "names no atlas"),
        ('[pointer]\natlas = "suite"\nrepo = "api"\n', 'holds "repo"'),
        ("[pointer]\natlas = 3\n", "not a string"),
        ('wm_version = "0.1.1"\n[pointer]\natlas = "suite"\n', 'holds "wm_version" beside'),
        ('atlas = "suite"\n', "no [pointer] table"),
    ],
)
def test_pointer_that_cant_be_read_says_why(text: str, problem: str) -> None:
    pointer, reason = parse_pointer(text)
    assert pointer is None
    assert reason is not None
    assert problem in reason


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("atlas = \n", ".waymark/atlas.toml is not valid TOML"),
        ('path = "../atlas"\n', "names no atlas"),
        ('atlas = "suite"\nrepo = "api"\n', 'holds "repo"'),
        ("atlas = 3\n", "not a string"),
    ],
)
def test_old_pointer_that_cant_be_read_says_why(text: str, problem: str) -> None:
    pointer, reason = parse_pointer(text, old=True)
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
    write_pointer(tmp_path / "suite-api", '[pointer]\natlas = "other"\n')
    assert locate_repo("suite", suite.root, API, empty(tmp_path)).found is Found.MISSING


def test_repo_hint_is_not_used_when_its_old_pointer_names_another_atlas(
    suite: Workspace, tmp_path: Path
) -> None:
    git_init(tmp_path / "suite-api")
    write_old_pointer(tmp_path / "suite-api", 'atlas = "other"\n')
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
    write_pointer(code, render_pointer(Pointer("suite", "../atlas", None)))
    (code / "src").mkdir()
    project = find_project(code / "src", empty(tmp_path))
    assert project.root == suite.root.resolve()
    assert project.code_repo == code.resolve()
    assert not project.old_pointer
    assert any("wm atlas register" in note for note in project.notes)


def test_project_is_found_from_a_code_repo_through_its_old_pointer(
    suite: Workspace, tmp_path: Path
) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    write_old_pointer(code, 'atlas = "suite"\npath = "../atlas"\n')
    (code / "src").mkdir()
    project = find_project(code / "src", empty(tmp_path))
    assert (project.root, project.code_repo) == (suite.root.resolve(), code.resolve())
    assert project.old_pointer


def test_old_pointer_comes_before_the_registry(suite: Workspace, tmp_path: Path) -> None:
    other = Workspace(tmp_path / "other", ATLAS_CONFIG.replace('"suite"', '"other"'))
    code = tmp_path / "suite-api"
    git_init(code)
    write_old_pointer(code, 'atlas = "suite"\npath = "../atlas"\n')
    registry = empty(tmp_path).with_atlas("other", other.root).with_repo("other", "api", code)
    project = find_project(code, registry)
    assert project.root == suite.root.resolve()
    assert project.old_pointer


def test_new_pointer_is_read_before_the_old_one(suite: Workspace, tmp_path: Path) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    write_pointer(code, '[pointer]\natlas = "suite"\npath = "../atlas"\n')
    write_old_pointer(code, 'atlas = "other"\n')
    project = find_project(code, empty(tmp_path))
    assert project.root == suite.root.resolve()
    assert not project.old_pointer


def test_records_settings_are_not_taken_for_a_pointer(suite: Workspace, tmp_path: Path) -> None:
    project = find_project(suite.root, empty(tmp_path))
    assert (project.root, project.code_repo, project.old_pointer) == (suite.root, None, False)


def test_broken_pointer_is_reported_as_a_pointer(tmp_path: Path) -> None:
    code = tmp_path / "suite-api"
    git_init(code)
    write_pointer(code, '[pointer]\npath = "../atlas"\n')
    with pytest.raises(ProjectNotFoundError, match=r"pointer: waymark/config.toml names no atlas"):
        find_project(code, empty(tmp_path))


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
    write_pointer(code, '[pointer]\natlas = "suite"\npath = "../atlas"\n')
    with pytest.raises(ProjectNotFoundError, match=r'points to the atlas "suite".*Clone it'):
        find_project(code, empty(tmp_path))

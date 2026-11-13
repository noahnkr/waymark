"""The per-machine registry: where it lives, and what it holds."""

from pathlib import Path

import pytest

from waymark.record.registry import (
    REGISTRY_ENV,
    Registry,
    load_registry,
    parse_registry,
    registry_path,
    render_registry,
    stage_registry,
)

HOME = Path("/home/sam")


@pytest.mark.parametrize(
    ("platform", "environ", "expected"),
    [
        ("win32", {"APPDATA": "C:/Users/sam/Roaming"}, Path("C:/Users/sam/Roaming")),
        ("win32", {}, HOME / "AppData" / "Roaming"),
        ("darwin", {}, HOME / "Library" / "Application Support"),
        ("linux", {}, HOME / ".config"),
        ("linux", {"XDG_CONFIG_HOME": "/srv/settings"}, Path("/srv/settings")),
        ("linux", {"XDG_CONFIG_HOME": "relative/settings"}, HOME / ".config"),
    ],
)
def test_registry_lives_in_the_platforms_user_settings_folder(
    platform: str, environ: dict[str, str], expected: Path
) -> None:
    path = registry_path(environ, platform, HOME)
    assert path == expected / "waymark" / "registry.toml"


def test_registry_path_is_overridden_by_the_environment() -> None:
    environ = {REGISTRY_ENV: "/tmp/elsewhere.toml", "APPDATA": "C:/x"}
    assert registry_path(environ, "win32", HOME) == Path("/tmp/elsewhere.toml")


def test_registry_round_trips_atlases_and_repos(tmp_path: Path) -> None:
    registry = (
        Registry(tmp_path / "registry.toml")
        .with_atlas("my.suite", Path("C:\\work\\suite"))
        .with_repo("my.suite", "api", Path("C:\\work\\suite-api"))
        .with_repo("other", "web", Path("/srv/web"))
    )
    again = parse_registry(registry.path, render_registry(registry))
    assert again.problems == ()
    assert again.atlas("my.suite") is not None
    assert again.repo("my.suite", "api") == Path("C:\\work\\suite-api")
    assert again.repo("other", "web") == Path("/srv/web")
    assert again.atlas("other") is not None
    assert again.atlases["other"].path is None


def test_registering_an_atlas_again_keeps_its_repos(tmp_path: Path) -> None:
    registry = (
        Registry(tmp_path / "r.toml")
        .with_repo("suite", "api", tmp_path / "api")
        .with_atlas("suite", tmp_path / "moved")
    )
    assert registry.repo("suite", "api") == tmp_path / "api"
    assert registry.atlases["suite"].path == tmp_path / "moved"


def test_a_registry_that_doesnt_exist_yet_is_empty(tmp_path: Path) -> None:
    registry = load_registry(tmp_path / "none.toml")
    assert registry.atlases == {}
    assert registry.problems == ()


def test_a_registry_that_cant_be_read_reports_why(tmp_path: Path) -> None:
    broken = parse_registry(tmp_path / "r.toml", "[atlases.suite\n")
    assert "not valid TOML" in broken.problems[0]
    stray = parse_registry(tmp_path / "r.toml", 'other = "x"\n')
    assert "[atlases.<name>]" in stray.problems[0]
    no_path = parse_registry(tmp_path / "r.toml", "[atlases.suite.repos.api]\n")
    assert 'code repo "api" of the atlas "suite" has no path' in no_path.problems[0]


def test_registry_is_written_whole_to_its_folder(tmp_path: Path) -> None:
    path = tmp_path / "settings" / "waymark" / "registry.toml"
    registry = Registry(path).with_atlas("suite", tmp_path / "suite")
    stage_registry(registry).commit()
    assert load_registry(path).atlases["suite"].path == tmp_path / "suite"
    assert path.read_text(encoding="utf-8").startswith("# The atlases and code repos")

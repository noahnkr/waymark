"""Settings in config.toml."""

import pytest

from tests.support import ATLAS_CONFIG, CONFIG
from waymark import __version__
from waymark.record.config import CodeRepo, Reference, parse_config
from waymark.record.terms import Layout, ReviewLevel


def codes(text: str) -> list[str]:
    config, problems = parse_config(text)
    assert config is None
    return [problem.code for problem in problems]


def test_config_holds_the_pinned_version_default_review_and_agent_tools() -> None:
    config, problems = parse_config(CONFIG)
    assert problems == ()
    assert config is not None
    assert config.wm_version == __version__
    assert config.record_format == 1
    assert config.default_review is ReviewLevel.SELF
    assert config.agent_tools == ("some-tool",)


def test_commit_scopes_are_optional() -> None:
    without, _ = parse_config(CONFIG)
    with_scopes, _ = parse_config(CONFIG + 'commit_scopes = ["cli", "record"]\n')
    assert without is not None
    assert with_scopes is not None
    assert without.commit_scopes is None
    assert with_scopes.commit_scopes == ("cli", "record")


def test_record_without_an_atlas_table_lives_in_the_repo() -> None:
    config, _ = parse_config(CONFIG)
    assert config is not None
    assert config.layout is Layout.REPO
    assert config.repos == ()


def test_references_name_other_atlases_with_optional_path_hints() -> None:
    text = CONFIG + '\n[references.billing]\npath = "../billing"\n\n[references.auth]\n'
    config, problems = parse_config(text)
    assert problems == ()
    assert config is not None
    assert config.references == (Reference("billing", "../billing"), Reference("auth", None))


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ('\n[references.billing]\nbranch = "main"\n', '"branch" is not a setting'),
        ('\nreferences = ["billing"]\n', '"[references.<atlas>]" table'),
        ('\n[atlas]\nname = "suite"\n\n[references.suite]\n', "can't reference itself"),
    ],
)
def test_reference_that_cant_be_read_is_a_problem(text: str, problem: str) -> None:
    config, problems = parse_config(CONFIG + text)
    assert config is None
    assert any(problem in found.message for found in problems)


def test_atlas_names_its_code_repos_with_optional_path_hints() -> None:
    config, problems = parse_config(ATLAS_CONFIG)
    assert problems == ()
    assert config is not None
    assert config.layout is Layout.ATLAS
    assert config.atlas_name == "suite"
    assert config.repos == (CodeRepo("api", "../suite-api"), CodeRepo("web", None))


def test_atlas_may_name_no_repos_yet() -> None:
    config, problems = parse_config(CONFIG + '\n[atlas]\nname = "suite"\n')
    assert problems == ()
    assert config is not None
    assert config.layout is Layout.ATLAS


def test_unknown_setting_is_a_problem() -> None:
    assert codes(CONFIG + "tint = true\n") == ["unknown-setting"]


def test_unknown_review_level_is_a_problem() -> None:
    assert codes(CONFIG.replace('"self"', '"strict"')) == ["invalid-setting"]


def test_missing_pinned_version_is_a_problem() -> None:
    assert codes(CONFIG.replace(f'wm_version = "{__version__}"\n', "")) == ["invalid-setting"]


def test_record_format_number_is_required() -> None:
    assert codes(CONFIG.replace("record_format = 1\n", "")) == ["invalid-setting"]
    assert codes(CONFIG.replace("record_format = 1", "record_format = 0")) == ["invalid-setting"]


def test_invalid_toml_is_a_problem() -> None:
    assert codes("wm_version = \n") == ["invalid-toml"]

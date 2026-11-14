"""Setting up a project and creating artifacts from the built-in templates."""

import datetime
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import Workspace
from waymark import __version__, adapters
from waymark.record.files import RecordFiles
from waymark.record.githooks import hook_files
from waymark.record.project import find_project
from waymark.record.record import load_record
from waymark.record.state import ExplorationStatus, StepKind, derive_state
from waymark.record.terms import Layout, Phase
from waymark.services import check, integration, lifecycle, setup
from waymark.services.common import Refusal

TODAY = datetime.date(2026, 1, 15)


def test_init_refuses_outside_a_git_repository(tmp_path: Path) -> None:
    with pytest.raises(Refusal, match="git init"):
        setup.init_project(tmp_path)
    assert not (tmp_path / "waymark").exists()


def test_init_creates_the_settings_and_a_charter_skeleton(tmp_path: Path) -> None:
    git_init(tmp_path)
    done = setup.init_project(tmp_path)
    assert {"waymark/charter.md", "waymark/config.toml"} <= set(done.paths)
    assert "wm-kickoff" in done.message
    record = load_record(find_project(tmp_path))
    assert record.problems == ()
    assert record.config is not None
    assert record.config.wm_version == __version__
    assert record.config.record_format == 1
    assert record.layout is Layout.REPO
    assert record.charter is not None
    assert record.charter.title == tmp_path.name


def test_init_pins_the_version_that_created_the_project(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    text = (tmp_path / "waymark" / "config.toml").read_text(encoding="utf-8")
    assert f'wm_version = "{__version__}"' in text


def test_init_as_an_atlas_names_the_atlas(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path, atlas="suite")
    record = load_record(find_project(tmp_path))
    assert record.problems == ()
    assert record.layout is Layout.ATLAS
    assert record.config is not None
    assert record.config.atlas_name == "suite"
    other = tmp_path / "other"
    git_init(other)
    with pytest.raises(Refusal, match="atlas name"):
        setup.init_project(other, atlas="not a name")
    assert not (other / "waymark").exists()


def test_init_puts_the_record_at_the_top_of_the_repository(tmp_path: Path) -> None:
    git_init(tmp_path)
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    setup.init_project(nested)
    assert (tmp_path / "waymark" / "config.toml").is_file()
    assert not (nested / "waymark").exists()


def test_init_refuses_when_the_repository_already_has_a_record(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    before = (tmp_path / "waymark" / "charter.md").read_bytes()
    with pytest.raises(Refusal, match="already has a record"):
        setup.init_project(tmp_path)
    assert (tmp_path / "waymark" / "charter.md").read_bytes() == before


def test_ignore_patterns_list_the_shared_skills_each_tool_and_the_hooks() -> None:
    tools = adapters.names()
    expected = ["/.agents/skills/wm-*/"]
    for tool in tools:
        expected += adapters.get(tool).ignored
    expected.append("/.waymark/hooks/")
    assert integration.ignore_patterns(tools, record=True) == expected
    assert integration.ignore_patterns((), record=True) == [
        "/.agents/skills/wm-*/",
        "/.waymark/hooks/",
    ]


def test_ignore_patterns_without_a_record_list_only_the_hooks() -> None:
    assert integration.ignore_patterns(adapters.names(), record=False) == ["/.waymark/hooks/"]


def test_ignore_patterns_refuse_a_tool_wm_does_not_know() -> None:
    with pytest.raises(Refusal, match="not an agent tool"):
        integration.ignore_patterns(("no-such-tool",), record=True)


def ignored_by_git(root: Path, patterns: list[str], paths: list[str]) -> set[str]:
    """The paths that git ignores in a fresh repository whose .gitignore holds the patterns."""
    git_init(root)
    (root / ".gitignore").write_text("".join(f"{line}\n" for line in patterns), encoding="utf-8")
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", "--stdin"],
        input="".join(f"{path}\n" for path in paths).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return set(result.stdout.decode("utf-8").splitlines())


def test_every_file_wm_writes_for_a_machine_is_ignored(tmp_path: Path) -> None:
    tools = adapters.names()
    rendered = sorted(integration.integration_files(RecordFiles(tmp_path), tools))
    hooks = sorted(hook_files())
    assert rendered
    assert hooks
    paths = rendered + hooks
    root = tmp_path / "repo"
    ignored = ignored_by_git(root, integration.ignore_patterns(tools, record=True), paths)
    assert ignored == set(paths)


def test_the_patterns_leave_the_projects_own_files_alone(tmp_path: Path) -> None:
    own = [
        "waymark/config.toml",
        ".waymark/atlas.toml",
        ".gitignore",
        ".claude/skills/team-skill/SKILL.md",
        ".claude/agents/helper.md",
        ".agents/skills/team-skill/SKILL.md",
        "docs/.claude/settings.json",
    ]
    patterns = integration.ignore_patterns(adapters.names(), record=True)
    assert ignored_by_git(tmp_path / "repo", patterns, own) == set()


def test_new_change_writes_a_proposal_owned_by_the_git_user(project: Workspace) -> None:
    done = setup.create_change(project.root, "add-limit")
    assert done.paths == ("changes/add-limit/proposal.md",)
    change = project.record().changes["add-limit"]
    assert change.proposal is not None
    assert change.proposal.owner == "Sam Doe"
    assert change.proposal.title == "Add limit"
    assert not change.short_path
    state = project.change_state()
    assert (state.phase, state.next_step.kind) == (Phase.PROPOSED, StepKind.PROPOSE)


def test_new_change_can_name_another_owner_and_take_the_short_path(project: Workspace) -> None:
    setup.create_change(project.root, "fix-typo", short=True, owner="Robin Roe")
    change = project.record().changes["fix-typo"]
    assert change.proposal is not None
    assert change.proposal.owner == "Robin Roe"
    assert change.short_path


def test_new_change_needs_an_owner(workspace: Workspace) -> None:
    git_init(workspace.root, name=None)
    with pytest.raises(Refusal, match="--owner"):
        setup.create_change(workspace.root, "add-limit")
    assert workspace.record().changes == {}


@pytest.mark.parametrize("name", ["Add-Limit", "add_limit", "add-limit-2", ""])
def test_new_change_refuses_a_name_that_breaks_the_naming_rule(
    project: Workspace, name: str
) -> None:
    with pytest.raises(Refusal, match="lowercase words"):
        setup.create_change(project.root, name)


def test_new_change_refuses_a_name_already_in_use(project: Workspace) -> None:
    setup.create_change(project.root, "add-limit")
    with pytest.raises(Refusal, match="already is a change"):
        setup.create_change(project.root, "add-limit")


def test_new_milestone_writes_a_goal_and_a_roadmap(project: Workspace) -> None:
    done = setup.create_milestone(project.root, "faster-search")
    assert done.paths == (
        "milestones/faster-search/goal.md",
        "milestones/faster-search/roadmap.md",
    )
    record = project.record()
    milestone = record.milestones["faster-search"]
    assert milestone.goal is not None
    assert milestone.roadmap is not None
    assert milestone.roadmap.entries == ()
    assert check.check_record(record, datetime.datetime.now(datetime.UTC)) != ()
    with pytest.raises(Refusal, match="already is a milestone"):
        setup.create_milestone(project.root, "faster-search")


def test_new_exploration_starts_open(project: Workspace) -> None:
    setup.create_exploration(project.root, "paging")
    record = project.record()
    assert record.problems == ()
    assert derive_state(record).explorations["paging"].status is ExplorationStatus.OPEN
    with pytest.raises(Refusal, match="already is an exploration"):
        setup.create_exploration(project.root, "paging")


def test_writes_are_refused_when_the_pinned_version_differs(project: Workspace) -> None:
    project.change()
    project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    attempts: tuple[Callable[[], object], ...] = (
        lambda: setup.create_change(project.root, "add-order"),
        lambda: setup.create_exploration(project.root, "paging"),
        lambda: lifecycle.accept(project.root, "add-limit", TODAY),
        lambda: lifecycle.tick(project.root, "add-limit", "1.1"),
        lambda: lifecycle.archive(project.root, "add-limit", TODAY, outcome="Done."),
    )
    for attempt in attempts:
        with pytest.raises(Refusal) as refusal:
            attempt()
        assert "pinned to wm 9.9.9" in str(refusal.value)
        assert "waymark-cli==9.9.9" in str(refusal.value)
    assert list(project.record().changes) == ["add-limit"]


def test_reads_still_work_when_the_pinned_version_differs(project: Workspace) -> None:
    project.change()
    project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    findings = check.check(project.root, datetime.datetime.now(datetime.UTC))
    assert [finding.code for finding in findings] == ["version-pin"]
    assert not check.has_errors(findings)


def test_writes_are_refused_when_the_record_format_differs(project: Workspace) -> None:
    project.replace("config.toml", "record_format = 1", "record_format = 2")
    with pytest.raises(Refusal, match="wm update"):
        setup.create_change(project.root, "add-limit")


def test_writes_are_refused_when_the_settings_are_broken(project: Workspace) -> None:
    project.replace("config.toml", 'default_review = "self"', 'default_review = "strict"')
    with pytest.raises(Refusal, match=r"config\.toml has problems"):
        setup.create_change(project.root, "add-limit")


def test_commands_outside_a_project_say_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(Refusal, match="initialize"):
        setup.create_change(tmp_path, "add-limit")

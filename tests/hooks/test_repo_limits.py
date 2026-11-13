"""Edit limits across an atlas's code repos, checked against where each repo is."""

import datetime
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, DESIGN, Workspace, delta, requirement
from waymark.hooks.decide import decide, working_repos
from waymark.hooks.events import Decision, Event, EventKind, Role
from waymark.services import lifecycle
from waymark.services.atlas import register

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
TASKS = (
    "# Tasks\n\n## 1. Limit\n\n"
    "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty at most\n  - Repo: api\n"
    "- [ ] 1.2 Show the list\n  - Criteria: fifty rows\n  - Repo: web\n"
)


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    """An accepted change in an atlas with both code repos on this machine."""
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG.replace('"some-tool"', '"claude-code"'))
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    git_init(tmp_path / "web")
    register(atlas.root)
    register(atlas.root, "web", "../web")
    atlas.change(
        deltas={"search": delta(added=(requirement(),), purpose="How search works.")},
        design=DESIGN,
        tasks=TASKS,
    )
    lifecycle.accept(atlas.root, NAME, DAY)
    return atlas


def edit(atlas: Workspace, path: Path, role: Role) -> Decision:
    return decide(Event(EventKind.EDIT, atlas.root, role, path=path, content="x"), DAY)


def test_implementer_may_edit_inside_the_repo_of_the_item_being_applied(
    suite: Workspace, tmp_path: Path
) -> None:
    assert working_repos(suite.record()) == {"api": [f"{NAME} 1.1"]}
    assert edit(suite, tmp_path / "suite-api" / "src" / "app.py", Role.IMPLEMENTER).allow


def test_implementer_edit_in_another_code_repo_is_refused(suite: Workspace, tmp_path: Path) -> None:
    decision = edit(suite, tmp_path / "web" / "page.html", Role.IMPLEMENTER)
    assert not decision.allow
    assert '"api"' in decision.reason
    assert f"{NAME} 1.1" in decision.reason


def test_implementer_edit_outside_every_repo_is_refused_in_an_atlas(
    suite: Workspace, tmp_path: Path
) -> None:
    for path in (tmp_path / "notes.txt", suite.root / "README.md"):
        assert not edit(suite, path, Role.IMPLEMENTER).allow


def test_the_allowed_repo_moves_on_with_the_next_item(suite: Workspace, tmp_path: Path) -> None:
    lifecycle.tick(suite.root, NAME, "1.1")
    lifecycle.self_review(suite.root, NAME, "1.1", "fine", DAY)
    assert working_repos(suite.record()) == {"web": [f"{NAME} 1.2"]}
    assert edit(suite, tmp_path / "web" / "page.html", Role.IMPLEMENTER).allow
    assert not edit(suite, tmp_path / "suite-api" / "app.py", Role.IMPLEMENTER).allow


def test_no_repo_is_open_to_implementers_while_no_item_is_to_apply(
    suite: Workspace, tmp_path: Path
) -> None:
    suite.replace(f"changes/{NAME}/tasks.md", "fifty at most", "at most fifty")
    assert working_repos(suite.record()) == {}
    decision = edit(suite, tmp_path / "suite-api" / "app.py", Role.IMPLEMENTER)
    assert not decision.allow
    assert "No accepted change has an item to apply" in decision.reason


def test_planner_edit_inside_a_code_repo_is_refused_in_an_atlas(
    suite: Workspace, tmp_path: Path
) -> None:
    decision = edit(suite, tmp_path / "suite-api" / "app.py", Role.PLANNER)
    assert not decision.allow
    assert "The planner edits only the record" in decision.reason
    assert edit(suite, suite.root / "README.md", Role.PLANNER).allow


def test_a_repo_found_through_its_hint_is_checked_the_same_way(tmp_path: Path) -> None:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    atlas.change(tasks=TASKS.split("- [ ] 1.2", maxsplit=1)[0], design=DESIGN)
    lifecycle.accept(atlas.root, NAME, DAY)
    assert edit(atlas, tmp_path / "suite-api" / "app.py", Role.IMPLEMENTER).allow
    assert not edit(atlas, tmp_path / "suite-api" / "app.py", Role.PLANNER).allow


def test_in_repo_layout_keeps_code_edits_open(project: Workspace) -> None:
    assert edit(project, project.root / "src" / "app.py", Role.IMPLEMENTER).allow
    assert edit(project, project.root / "src" / "app.py", Role.PLANNER).allow

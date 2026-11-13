"""Each touched repo's branch in an atlas's status, with a warning on a mismatch."""

import datetime
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, DESIGN, Workspace
from tests.views.validator import errors
from waymark.services import lifecycle
from waymark.views import payloads, render
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
TASKS = "# Tasks\n\n## 1. Limit\n\n- [ ] 1.1 Add the endpoint\n  - Criteria: fifty\n  - Repo: api\n"


def switch(folder: Path, branch: str) -> None:
    subprocess.run(
        ["git", "-C", str(folder), "switch", "--quiet", "-c", branch],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    atlas.change(design=DESIGN, tasks=TASKS)
    return atlas


def repos(atlas: Workspace) -> list[dict[str, Any]]:
    payload = payloads.status(atlas.record())
    assert errors(render.public(payload), SCHEMAS["status"]) == []
    change: dict[str, Any] = payload["changes"][0]
    result: list[dict[str, Any]] = change["repos"]
    return result


def test_status_shows_the_branch_of_the_atlas_and_each_repo_a_change_touches(
    suite: Workspace, tmp_path: Path
) -> None:
    switch(suite.root, NAME)
    switch(tmp_path / "suite-api", "main-line")
    found = repos(suite)
    assert [(r["name"], r["kind"], r["branch"]) for r in found] == [
        ("suite", "atlas", NAME),
        ("api", "code", "main-line"),
    ]
    assert [r["matches"] for r in found] == [True, False]


def test_branch_mismatch_warns_only_while_the_accepted_change_is_being_applied(
    suite: Workspace, tmp_path: Path
) -> None:
    switch(tmp_path / "suite-api", "other")
    assert not any(r["warn"] for r in repos(suite))
    lifecycle.accept(suite.root, NAME, DAY)
    assert [r["warn"] for r in repos(suite)] == [True, True]
    text = render.to_text(payloads.status(suite.record()), Style())
    assert f"api is on other, not on {NAME}" in text
    switch(suite.root, NAME)
    switch(tmp_path / "suite-api", NAME)
    assert not any(r["warn"] for r in repos(suite))
    lifecycle.tick(suite.root, NAME, "1.1")
    lifecycle.self_review(suite.root, NAME, "1.1", "fine", DAY)
    switch(tmp_path / "suite-api", "next")
    assert not any(r["warn"] for r in repos(suite))


def test_a_repo_not_on_this_machine_is_shown_without_a_branch(tmp_path: Path) -> None:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    atlas.change(design=DESIGN, tasks=TASKS)
    lifecycle.accept(atlas.root, NAME, DAY)
    api = repos(atlas)[1]
    assert (api["found"], api["branch"], api["warn"]) == (False, None, False)
    assert "api (not here)" in render.to_text(payloads.status(atlas.record()), Style())


def test_status_in_the_repo_layout_lists_no_repos(project: Workspace) -> None:
    project.change()
    assert payloads.status(project.record())["changes"][0]["repos"] == []

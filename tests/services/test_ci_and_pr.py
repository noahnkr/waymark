"""The CI workflow, and pull request text described from a change."""

import datetime
import subprocess
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace, delta, requirement
from tests.views.validator import errors
from waymark import __version__
from waymark.services import integration, lifecycle
from waymark.services.ci import WORKFLOW, add_workflow
from waymark.services.common import Refusal
from waymark.services.pr import describe, web_url
from waymark.views import render
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
TOOL_CONFIG = CONFIG.replace('"some-tool"', '"claude-code"')
ATLAS_TASKS = (
    "# Tasks\n\n## 1. Limit\n\n"
    "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty at most\n  - Repo: api\n"
    "- [ ] 1.2 Show the list   `review: none`\n  - Criteria: fifty rows\n  - Repo: web\n"
)


def remote(root: Path, url: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", url], check=True, capture_output=True
    )


def test_ci_workflow_installs_the_pinned_wm_and_runs_check(project: Workspace) -> None:
    done = add_workflow(project.root)
    assert f"created: {WORKFLOW}" in done.message
    text = (project.root / WORKFLOW).read_text(encoding="utf-8")
    assert "waymark/config.toml" in text
    assert "['wm_version']" in text
    assert 'pip install "waymark-cli==$version"' in text
    assert text.rstrip().endswith("run: wm check")
    assert __version__ not in text
    assert "already current" in add_workflow(project.root).message


def test_ci_workflow_needs_the_pinned_wm(project: Workspace) -> None:
    project.write("config.toml", CONFIG.replace(__version__, "9.9.9"))
    with pytest.raises(Refusal, match=r"pinned to wm 9\.9\.9"):
        add_workflow(project.root)


def test_update_refreshes_the_workflow_only_when_it_is_there(tmp_path: Path) -> None:
    project = Workspace(tmp_path / "p", TOOL_CONFIG)
    git_init(project.root)
    integration.update(project.root)
    assert not (project.root / WORKFLOW).exists()
    add_workflow(project.root)
    (project.root / WORKFLOW).write_text("old\n", encoding="utf-8")
    assert f"updated: {WORKFLOW}" in integration.update(project.root).message


@pytest.mark.parametrize(
    ("url", "web"),
    [
        ("git@github.com:someone/shop.git", "https://github.com/someone/shop"),
        ("https://github.com/someone/shop.git", "https://github.com/someone/shop"),
        ("https://token@github.com/someone/shop", "https://github.com/someone/shop"),
        ("ssh://git@github.com/someone/shop.git", "https://github.com/someone/shop"),
        ("git@gitlab.com:someone/shop.git", None),
        ("/srv/git/shop.git", None),
        (None, None),
    ],
)
def test_web_address_comes_from_the_remote_and_only_for_github(
    url: str | None, web: str | None
) -> None:
    assert web_url(url) == web


def test_pr_text_is_drawn_from_the_change(project: Workspace) -> None:
    project.change()
    remote(project.root, "git@github.com:someone/shop.git")
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    payload = describe(project.record(), NAME)
    assert errors(payload, SCHEMAS["pr"]) == []
    assert (payload["title"], payload["branch"], payload["repo"]) == (
        "Limit the results",
        NAME,
        None,
    )
    body = payload["body"]
    assert body.startswith("Long result lists are slow.")
    assert "## What changes\n\nSearch returns a capped list." in body
    assert "- search: adds Result limit" in body
    assert "- [x] 1.1 Cap the result count (self-reviewed)" in body
    assert "- [ ] 1.2 Document the limit (not built yet)" in body
    url = f"https://github.com/someone/shop/blob/{NAME}/waymark/changes/{NAME}/proposal.md"
    assert payload["links"] == [{"name": "change", "url": url}]
    assert f"- The change: [waymark/changes/{NAME}/proposal.md]({url})" in body
    assert "Title: Limit the results" in render.to_text(payload, Style())


def test_pr_text_without_a_github_remote_names_the_file_and_branch(project: Workspace) -> None:
    project.change()
    payload = describe(project.record(), NAME)
    assert payload["links"] == []
    assert (
        f"- The change: waymark/changes/{NAME}/proposal.md, on the branch {NAME}"
        in (payload["body"])
    )


@pytest.fixture
def suite(tmp_path: Path) -> Workspace:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    remote(atlas.root, "git@github.com:someone/suite.git")
    git_init(tmp_path / "suite-api")
    remote(tmp_path / "suite-api", "https://github.com/someone/suite-api.git")
    atlas.change(
        deltas={"search": delta(added=(requirement(),), purpose="How search works.")},
        tasks=ATLAS_TASKS,
    )
    return atlas


def test_pr_in_a_code_repo_lists_its_items_and_links_the_other_repos(suite: Workspace) -> None:
    payload = describe(suite.record(), NAME, "api")
    body = payload["body"]
    assert "## Items in api" in body
    assert "1.1 Add the endpoint" in body
    assert "1.2" not in body
    names = [link["name"] for link in payload["links"]]
    assert names == ["change", "suite"]
    assert payload["links"][1]["url"] == (
        f"https://github.com/someone/suite/pulls?q=is:pr%20head:{NAME}"
    )
    assert "- The pull request in web, from the branch add-limit" in body


def test_pr_for_the_atlas_lists_every_item_and_links_each_code_repo(suite: Workspace) -> None:
    payload = describe(suite.record(), NAME)
    assert "1.1 Add the endpoint (not built yet, in api)" in payload["body"]
    assert "1.2 Show the list (not built yet, in web)" in payload["body"]
    assert [link["name"] for link in payload["links"]] == ["change", "api"]
    assert render.to_json(payload)


def test_pr_refuses_a_repo_the_change_doesnt_touch(suite: Workspace, project: Workspace) -> None:
    with pytest.raises(Refusal, match='no items in the repo "mobile"'):
        describe(suite.record(), NAME, "mobile")
    with pytest.raises(Refusal, match='no items in the repo "suite"'):
        describe(suite.record(), NAME, "suite")
    project.change()
    with pytest.raises(Refusal, match="keeps everything in one"):
        describe(project.record(), NAME, "api")
    with pytest.raises(Refusal, match="no active change"):
        describe(project.record(), "other")

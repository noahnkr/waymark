"""Requirement "Branch and base": a change's branch, its base, and whether its dependency merged."""

import subprocess
from pathlib import Path

from tests.support import Workspace, proposal
from waymark.record import git
from waymark.record.branches import Branches


def run(repository: Path, *arguments: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    )
    return done.stdout


def commit(repository: Path, name: str) -> None:
    (repository / f"{name}.txt").write_text(name, encoding="utf-8")
    run(repository, "add", f"{name}.txt")
    run(repository, "commit", "--quiet", "-m", name)


def on_main(repository: Path) -> None:
    """A first commit on a branch named main, whatever git's own default is."""
    run(repository, "symbolic-ref", "HEAD", "refs/heads/main")
    run(repository, "config", "user.email", "sam@example.com")
    commit(repository, "start")


def with_origin(repository: Path, tmp_path: Path, head: str = "main") -> Path:
    """A bare origin holding main, with its HEAD set to a branch."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(origin)], check=True)
    run(repository, "remote", "add", "origin", str(origin))
    run(repository, "push", "--quiet", "origin", "main")
    if head != "main":
        run(repository, "push", "--quiet", "origin", f"main:{head}")
    run(repository, "remote", "set-head", "origin", head)
    return origin


def after(other: str) -> str:
    return proposal().replace("- Owner: Sam Doe\n", f"- Owner: Sam Doe\n- After: {other}\n")


def test_default_branch_is_main_without_a_remote(project: Workspace) -> None:
    on_main(project.root)
    assert git.default_branch(project.root) == "main"


def test_default_branch_is_the_remotes_head(project: Workspace, tmp_path: Path) -> None:
    on_main(project.root)
    with_origin(project.root, tmp_path, head="trunk")
    assert git.default_branch(project.root) == "trunk"


def test_a_branch_merged_only_on_origin_is_merged(project: Workspace, tmp_path: Path) -> None:
    on_main(project.root)
    with_origin(project.root, tmp_path)
    run(project.root, "checkout", "--quiet", "-b", "add-limit")
    commit(project.root, "limit")
    run(project.root, "checkout", "--quiet", "main")
    assert not git.is_merged(project.root, "add-limit", "main")
    run(project.root, "push", "--quiet", "origin", "add-limit:main")
    run(project.root, "fetch", "--quiet", "origin")
    assert git.is_merged(project.root, "add-limit", "main")
    assert not git.is_merged(project.root, "add-nothing", "main")


def test_scenario_change_without_a_dependency(project: Workspace) -> None:
    on_main(project.root)
    project.change("add-limit")
    record = project.record()
    place = Branches(record).of(record.changes["add-limit"])
    assert (place.branch, place.base, place.after, place.merged) == (
        "add-limit",
        "main",
        None,
        False,
    )


def test_scenario_stacked_change(project: Workspace) -> None:
    on_main(project.root)
    run(project.root, "branch", "add-limit")
    run(project.root, "checkout", "--quiet", "add-limit")
    commit(project.root, "limit")
    project.change("add-limit")
    project.change("add-paging", proposal_text=after("add-limit"))
    record = project.record()
    place = Branches(record).of(record.changes["add-paging"])
    assert (place.branch, place.base, place.after, place.merged) == (
        "add-paging",
        "add-limit",
        "add-limit",
        False,
    )


def test_a_dependency_archived_in_the_record_is_merged(project: Workspace) -> None:
    on_main(project.root)
    project.write("changes/archive/2026-01-20-add-limit/proposal.md", proposal(outcome="Done."))
    project.change("add-paging", proposal_text=after("add-limit"))
    record = project.record()
    place = Branches(record).of(record.changes["add-paging"])
    assert (place.base, place.merged) == ("main", True)


def test_outside_git_the_base_is_main_and_nothing_is_merged(workspace: Workspace) -> None:
    workspace.change("add-limit")
    workspace.change("add-paging", proposal_text=after("add-limit"))
    record = workspace.record()
    place = Branches(record).of(record.changes["add-paging"])
    assert (place.base, place.merged) == ("add-limit", False)

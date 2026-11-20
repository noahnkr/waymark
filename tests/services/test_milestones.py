"""Closing a milestone."""

import datetime

import pytest

from tests.support import Workspace, proposal
from tests.support import milestone as milestone_text
from waymark.record.record import link_problems
from waymark.record.state import ExplorationStatus
from waymark.services import lifecycle, roadmap
from waymark.services.common import Refusal

DAY = datetime.date(2026, 2, 1)
NAME = "faster-search"
ARCHIVED_CHANGE = "changes/archive/2026-01-20-add-limit"


def milestone(project: Workspace, *lines: str) -> Workspace:
    project.write(f"milestones/{NAME}/milestone.md", milestone_text("".join(lines)))
    return project


def refused(project: Workspace) -> str:
    with pytest.raises(Refusal) as refusal:
        lifecycle.close_milestone(project.root, NAME, DAY)
    assert project.path(f"milestones/{NAME}/milestone.md").is_file()
    return str(refusal.value)


def test_milestone_with_an_active_change_cannot_be_closed(project: Workspace) -> None:
    project.change("add-order")
    milestone(project, "- [ ] [Order](../../changes/add-order/proposal.md)\n")
    assert "add-order is still active" in refused(project)


def test_milestone_linking_to_a_change_that_is_gone_cannot_be_closed(project: Workspace) -> None:
    milestone(project, "- [ ] [Cache](../../changes/add-cache/proposal.md)\n")
    assert "add-cache, which can't be found" in refused(project)


def test_closing_moves_the_milestone_to_the_dated_archive(project: Workspace) -> None:
    project.write(f"{ARCHIVED_CHANGE}/proposal.md", proposal(outcome="Done."))
    milestone(
        project,
        f"- [x] [Limit](../../{ARCHIVED_CHANGE}/proposal.md)\n",
        "- add-paging: never proposed\n",
    )
    with pytest.raises(Refusal) as refusal:
        lifecycle.close_milestone(project.root, NAME, DAY)
    assert "add-paging: never proposed" in str(refusal.value)
    assert "wm roadmap drop" in str(refusal.value)
    assert NAME in project.record().milestones
    roadmap.drop(project.root, NAME, "add-paging", "paging can wait", DAY)
    done = lifecycle.close_milestone(project.root, NAME, DAY)
    target = f"milestones/archive/2026-02-01-{NAME}"
    assert target in done.message
    record = project.record()
    assert record.problems == ()
    assert record.milestones == {}
    assert [(entry.name, entry.date) for entry in record.archived_milestones] == [(NAME, DAY)]
    closed = project.read(f"{target}/milestone.md")
    assert closed.startswith(
        milestone_text(f"- [x] [Limit](../../../{ARCHIVED_CHANGE}/proposal.md)\n")
    )
    assert closed.endswith(
        "- 2026-02-01 (dropped) add-paging by planner for Sam Doe: paging can wait\n"
    )


def exploration(status: str, milestone_link: str = f"../milestones/{NAME}/milestone.md") -> str:
    return (
        f"# Speed\n\n- **Status:** {status}\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        f"## Conclusion\n\n[Faster search]({milestone_link})\n\n## Related\n"
    )


def snapshot(project: Workspace) -> dict[str, bytes]:
    root = project.path("")
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_closing_rewrites_links_to_the_milestone(project: Workspace) -> None:
    milestone(project)
    project.change("add-order")
    project.write(
        "explorations/speed.md",
        exploration(
            f"led-to [Faster search](../milestones/{NAME}/milestone.md), "
            "[add-order](../changes/add-order/proposal.md)"
        ),
    )
    lifecycle.close_milestone(project.root, NAME, DAY)
    assert f"(../milestones/archive/2026-02-01-{NAME}/milestone.md)" in project.read(
        "explorations/speed.md"
    )
    assert link_problems(project.record()) == ()
    state = project.state().explorations["speed"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, f"milestone {NAME}")


def test_scenario_its_milestone_closed(project: Workspace) -> None:
    project.write(f"{ARCHIVED_CHANGE}/proposal.md", proposal(outcome="Done."))
    milestone(project, f"- [x] [Limit](../../{ARCHIVED_CHANGE}/proposal.md)\n")
    project.write(
        "explorations/speed.md",
        exploration(f"led-to [Faster search](../milestones/{NAME}/milestone.md)"),
    )
    done = lifecycle.close_milestone(project.root, NAME, DAY)
    moved = "explorations/archive/2026-02-01-speed.md"
    assert moved in done.paths
    assert not project.path("explorations/speed.md").exists()
    closed = f"../../milestones/archive/2026-02-01-{NAME}/milestone.md"
    assert project.read(moved) == exploration(f"led-to [Faster search]({closed})", closed)
    record = project.record()
    assert record.problems == ()
    assert record.explorations == {}
    assert [(entry.name, entry.date) for entry in record.archived_explorations] == [("speed", DAY)]


def test_closed_milestone_follows_its_exploration_to_the_archive(project: Workspace) -> None:
    """The closed milestone's own link to the exploration it came from is re-aimed too."""
    project.write(f"{ARCHIVED_CHANGE}/proposal.md", proposal(outcome="Done."))
    milestone(project, f"- [x] [Limit](../../{ARCHIVED_CHANGE}/proposal.md)\n")
    path = f"milestones/{NAME}/milestone.md"
    link = "From [speed](../../explorations/speed.md).\n\n"
    project.write(path, project.read(path).replace("## Goal\n\n", f"## Goal\n\n{link}", 1))
    project.write(
        "explorations/speed.md",
        exploration(f"led-to [Faster search](../milestones/{NAME}/milestone.md)"),
    )
    lifecycle.close_milestone(project.root, NAME, DAY)
    closed = project.read(f"milestones/archive/2026-02-01-{NAME}/milestone.md")
    assert "[speed](../../../explorations/archive/2026-02-01-speed.md)" in closed


def test_close_refused_when_an_exploration_of_the_name_was_archived_that_day(
    project: Workspace,
) -> None:
    milestone(project)
    project.write(
        "explorations/speed.md",
        exploration(f"led-to [Faster search](../milestones/{NAME}/milestone.md)"),
    )
    project.write("explorations/archive/2026-02-01-speed.md", exploration("dropped"))
    before = snapshot(project)
    message = refused(project)
    assert snapshot(project) == before
    assert "explorations/archive/2026-02-01-speed.md" in message
    assert '"speed"' in message


def test_unknown_milestone_is_refused_with_the_open_ones(project: Workspace) -> None:
    milestone(project)
    with pytest.raises(Refusal, match="Open milestones: faster-search"):
        lifecycle.close_milestone(project.root, "tidy-docs", DAY)


def test_milestone_cannot_be_closed_twice_in_a_day_under_one_name(project: Workspace) -> None:
    milestone(project)
    project.write(f"milestones/archive/2026-02-01-{NAME}/milestone.md", milestone_text())
    assert "already closed today" in refused(project)

"""Closing a milestone."""

import datetime

import pytest

from tests.support import Workspace, proposal
from waymark.record.record import link_problems
from waymark.record.state import ExplorationStatus
from waymark.services import lifecycle
from waymark.services.common import Refusal

DAY = datetime.date(2026, 2, 1)
NAME = "faster-search"
GOAL = "# G\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n"
ARCHIVED_CHANGE = "changes/archive/2026-01-20-add-limit"


def milestone(project: Workspace, *lines: str) -> Workspace:
    project.write(f"milestones/{NAME}/goal.md", GOAL)
    project.write(f"milestones/{NAME}/roadmap.md", "# Roadmap\n\n" + "".join(lines))
    return project


def refused(project: Workspace) -> str:
    with pytest.raises(Refusal) as refusal:
        lifecycle.close_milestone(project.root, NAME, DAY)
    assert project.path(f"milestones/{NAME}/goal.md").is_file()
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
        "- [ ] Paging, never proposed\n",
    )
    done = lifecycle.close_milestone(project.root, NAME, DAY)
    target = f"milestones/archive/2026-02-01-{NAME}"
    assert target in done.message
    assert "Never proposed: Paging, never proposed." in done.message
    record = project.record()
    assert record.problems == ()
    assert record.milestones == {}
    assert [(entry.name, entry.date) for entry in record.archived_milestones] == [(NAME, DAY)]
    assert project.read(f"{target}/roadmap.md") == (
        f"# Roadmap\n\n- [x] [Limit](../../../{ARCHIVED_CHANGE}/proposal.md)\n"
        "- [ ] Paging, never proposed\n"
    )
    assert project.read(f"{target}/goal.md") == GOAL


def test_closing_rewrites_links_to_the_milestone(project: Workspace) -> None:
    milestone(project)
    project.write(
        "explorations/speed.md",
        "# Speed\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        f"## Conclusion\n\n[Faster search](../milestones/{NAME}/goal.md)\n\n## Related\n",
    )
    lifecycle.close_milestone(project.root, NAME, DAY)
    assert f"(../milestones/archive/2026-02-01-{NAME}/goal.md)" in project.read(
        "explorations/speed.md"
    )
    assert link_problems(project.record()) == ()
    state = project.state().explorations["speed"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, f"milestone {NAME}")


def test_unknown_milestone_is_refused_with_the_open_ones(project: Workspace) -> None:
    milestone(project)
    with pytest.raises(Refusal, match="Open milestones: faster-search"):
        lifecycle.close_milestone(project.root, "tidy-docs", DAY)


def test_milestone_cannot_be_closed_twice_in_a_day_under_one_name(project: Workspace) -> None:
    milestone(project)
    project.write(f"milestones/archive/2026-02-01-{NAME}/goal.md", GOAL)
    assert "already closed today" in refused(project)

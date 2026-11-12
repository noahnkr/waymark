"""Archiving and syncing: the archive gate, the merge, the move and the links."""

import datetime

import pytest

from tests.support import TASKS, Workspace, delta, proposal, requirement, spec
from waymark.record.record import link_problems
from waymark.record.state import (
    AcceptanceState,
    ConflictKind,
    ExplorationStatus,
    RoadmapStatus,
    StepKind,
)
from waymark.record.terms import Phase, Verdict
from waymark.services import lifecycle
from waymark.services.common import Refusal

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
LATER = datetime.date(2026, 2, 1)
ARCHIVED = f"changes/archive/2026-02-01-{NAME}"
HEAD = "# Tasks\n\n## 1. Limit\n\n"
ONE_ITEM = HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n"
CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def applied(project: Workspace, name: str = NAME, **options: object) -> Workspace:
    """A change that is accepted, built and reviewed."""
    project.change(name, tasks=ONE_ITEM, **options)  # type: ignore[arg-type]
    lifecycle.accept(project.root, name, DAY)
    lifecycle.tick(project.root, name, "1.1")
    lifecycle.self_review(project.root, name, "1.1", "matches the criteria", DAY)
    assert project.change_state(name).applied
    return project


def snapshot(project: Workspace) -> dict[str, bytes]:
    root = project.path("")
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def refused(project: Workspace, **options: str) -> str:
    before = snapshot(project)
    with pytest.raises(Refusal) as refusal:
        lifecycle.archive(project.root, NAME, LATER, **options)
    assert snapshot(project) == before
    return str(refusal.value)


def test_archive_merges_the_deltas_and_moves_the_change_to_the_dated_archive(
    project: Workspace,
) -> None:
    applied(project)
    done = lifecycle.archive(project.root, NAME, LATER, outcome="Capped at fifty.")
    assert ARCHIVED in done.message
    record = project.record()
    assert record.problems == ()
    assert record.changes == {}
    assert [(entry.date, entry.name) for entry in record.archived_changes] == [(LATER, NAME)]
    assert not project.path(f"changes/{NAME}").exists()
    created = record.specs["search"]
    assert created.purpose == "How search behaves."
    assert [item.name for item in created.requirements] == ["Result limit"]
    assert "## Outcome\n\nCapped at fifty.\n" in project.read(f"{ARCHIVED}/proposal.md")
    assert project.path(f"{ARCHIVED}/tasks.md").is_file()
    assert project.path(f"{ARCHIVED}/specs/search.md").is_file()


def test_archive_merges_into_an_existing_spec(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    applied(project, deltas={"search": delta(modified=(CHANGED,))})
    lifecycle.archive(project.root, NAME, LATER, outcome="Lowered.")
    living = project.record().specs["search"]
    assert [item.name for item in living.requirements] == ["Result limit", "Empty query"]
    assert "twenty" in living.requirements[0].statement


def test_archive_is_refused_for_an_unaccepted_change_even_with_an_override(
    project: Workspace,
) -> None:
    project.change(tasks=ONE_ITEM.replace("- [ ]", "- [x]"))
    assert "not accepted" in refused(project, outcome="Done.")
    message = refused(project, outcome="Done.", override="no time")
    assert "not accepted" in message
    assert "can't be overridden" in message


def test_archive_is_refused_when_acceptance_was_withdrawn(project: Workspace) -> None:
    applied(project)
    project.replace(f"changes/{NAME}/proposal.md", "Paging.", "Paging and sorting.")
    assert "not accepted as it stands" in refused(project, outcome="Done.", override="no time")


def test_archive_is_refused_while_items_are_unticked_even_with_an_override(
    project: Workspace,
) -> None:
    project.change()
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    assert "item 1.2 is not ticked" in refused(project, outcome="Done.")
    assert "can't be overridden" in refused(project, outcome="Done.", override="no time")


def test_archive_is_refused_while_a_review_record_is_missing(project: Workspace) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    message = refused(project, outcome="Done.")
    assert "item 1.1 is missing the review record" in message
    assert "--override" in message


def test_archive_override_passes_missing_reviews_and_records_the_reason(
    project: Workspace,
) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.archive(
        project.root, NAME, LATER, outcome="Shipped.", override="reviewed in the pull request"
    )
    text = project.read(f"{ARCHIVED}/proposal.md")
    assert text.endswith(
        "## Outcome\n\nShipped.\n\nReview override: reviewed in the pull request\n"
    )
    assert project.record().changes == {}


def test_archive_override_also_passes_a_failed_review(project: Workspace) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "naming", DAY)
    assert "missing the review record" in refused(project, outcome="Shipped.")
    lifecycle.archive(project.root, NAME, LATER, outcome="Shipped.", override="naming is fine")
    assert project.record().changes == {}


def test_archive_override_is_refused_when_there_is_nothing_to_override(
    project: Workspace,
) -> None:
    applied(project)
    assert "nothing to override" in refused(project, outcome="Done.", override="just in case")


def test_archive_is_refused_on_a_conflict_even_with_an_override(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    applied(project, deltas={"search": delta(added=(requirement("Result order"),))})
    project.write("specs/search.md", spec(requirement(), requirement("Result order")))
    state = project.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert state.next_step.kind is StepKind.RESOLVE_CONFLICT
    assert "conflict" in refused(project, outcome="Done.")
    assert "can't be overridden" in refused(project, outcome="Done.", override="no time")


def test_archive_needs_an_outcome(project: Workspace) -> None:
    applied(project)
    assert "--outcome" in refused(project)


def test_archive_uses_an_outcome_already_written_in_the_proposal(project: Workspace) -> None:
    applied(project)
    text = project.read(f"changes/{NAME}/proposal.md")
    project.write(f"changes/{NAME}/proposal.md", text + "\n## Outcome\n\nWritten by hand.\n")
    assert "already has an outcome" in refused(project, outcome="Another.")
    lifecycle.archive(project.root, NAME, LATER)
    assert "Written by hand." in project.read(f"{ARCHIVED}/proposal.md")


def test_archive_of_the_same_name_twice_in_a_day_is_refused(project: Workspace) -> None:
    applied(project)
    project.write(f"{ARCHIVED}/proposal.md", proposal(outcome="Earlier."))
    assert "already archived today" in refused(project, outcome="Done.")


def test_archived_name_can_be_reused(project: Workspace) -> None:
    applied(project)
    lifecycle.archive(project.root, NAME, DAY, outcome="First.")
    project.change(tasks=ONE_ITEM, deltas={"search": delta(modified=(CHANGED,))})
    lifecycle.accept(project.root, NAME, LATER)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", LATER)
    lifecycle.archive(project.root, NAME, LATER, outcome="Second.")
    record = project.record()
    assert [entry.date for entry in record.archived_changes] == [DAY, LATER]
    assert record.problems == ()


def test_archive_rewrites_links_that_point_into_the_moved_folder(project: Workspace) -> None:
    applied(project)
    project.write(
        "explorations/paging.md",
        "# Paging\n\n## Context\n\nSee the [tasks](../changes/add-limit/tasks.md#limit).\n\n"
        "## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\n[add-limit](../changes/add-limit/)\n\n## Related\n",
    )
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    text = project.read("explorations/paging.md")
    assert f"[tasks](../{ARCHIVED}/tasks.md#limit)" in text
    assert f"[add-limit](../{ARCHIVED}/)" in text
    record = project.record()
    assert link_problems(record) == ()
    state = project.state().explorations["paging"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, "change add-limit")


def test_archive_rewrites_links_inside_the_moved_files(project: Workspace) -> None:
    project.write("specs/export.md", spec(title="Export"))
    (project.root / "README.md").write_text("hello\n", encoding="utf-8")
    applied(project)
    design = f"changes/{NAME}/design.md"
    project.replace(
        design,
        "Cut the result list after sorting.",
        "Cut the list; see [export](../../specs/export.md), the [tasks](tasks.md), "
        "the [readme](../../../README.md) and [the web](https://example.com/a.md).",
    )
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    text = project.read(f"{ARCHIVED}/design.md")
    assert "[export](../../../specs/export.md)" in text
    assert "[tasks](tasks.md)" in text
    assert "[readme](../../../../README.md)" in text
    assert "[the web](https://example.com/a.md)" in text


def test_archive_ticks_the_roadmap_line_and_the_milestone_moves_on(project: Workspace) -> None:
    applied(project)
    project.write(
        "milestones/faster-search/goal.md",
        "# G\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n",
    )
    project.write(
        "milestones/faster-search/roadmap.md",
        "# Roadmap\n\n- [ ] [Limit](../../changes/add-limit/proposal.md)\n- [ ] Paging later\n",
    )
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    assert project.read("milestones/faster-search/roadmap.md") == (
        f"# Roadmap\n\n- [x] [Limit](../../{ARCHIVED}/proposal.md)\n- [ ] Paging later\n"
    )
    milestone = project.state().milestones["faster-search"]
    assert [line.status for line in milestone.lines] == [
        RoadmapStatus.ARCHIVED,
        RoadmapStatus.PLANNED,
    ]
    assert (milestone.archived, milestone.total) == (1, 1)
    assert link_problems(project.record()) == ()


def test_archive_leaves_unrelated_files_untouched(project: Workspace) -> None:
    project.write("specs/export.md", spec(title="Export"))
    project.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    applied(project)
    before = snapshot(project)
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    after = snapshot(project)
    for path in ("charter.md", "config.toml", "specs/export.md", "changes/add-order/tasks.md"):
        assert after[path] == before[path]


def test_failed_archive_leaves_the_record_as_it_was(project: Workspace) -> None:
    applied(project)
    project.write("changes/archive", "a file where the archive folder should be\n")
    before = snapshot(project)
    with pytest.raises(Refusal, match="Nothing was changed"):
        lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    assert snapshot(project) == before
    assert not project.path("specs/search.md").exists()
    assert project.change_state().applied


def test_second_archive_of_overlapping_changes_is_blocked_until_accepted_again(
    project: Workspace,
) -> None:
    project.write("specs/search.md", spec())
    for name, limit in (("fix-limit", "twenty"), ("cut-limit", "ten")):
        changed = requirement(statement=f"A search SHALL return at most {limit} results.")
        applied(project, name, deltas={"search": delta(modified=(changed,))})
    assert [c.kind for c in project.state().overlaps] == [ConflictKind.OVERLAP]

    lifecycle.archive(project.root, "fix-limit", LATER, outcome="Twenty.")
    state = project.change_state("cut-limit")
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert state.phase is Phase.PLANNED
    with pytest.raises(Refusal, match="not accepted as it stands"):
        lifecycle.archive(project.root, "cut-limit", LATER, outcome="Ten.")
    assert "twenty" in project.read("specs/search.md")

    lifecycle.accept(project.root, "cut-limit", LATER)
    lifecycle.archive(project.root, "cut-limit", LATER, outcome="Ten.")
    assert "at most ten results" in project.read("specs/search.md")
    assert project.state().overlaps == ()


def test_sync_is_refused_unless_the_change_is_applied(project: Workspace) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    with pytest.raises(Refusal, match="Only an applied change can be synced"):
        lifecycle.sync(project.root, NAME, LATER)
    lifecycle.tick(project.root, NAME, "1.1")
    with pytest.raises(Refusal, match="Only an applied change can be synced"):
        lifecycle.sync(project.root, NAME, LATER)
    assert not project.path("specs/search.md").exists()


def test_sync_merges_the_deltas_and_keeps_the_change_active_and_accepted(
    project: Workspace,
) -> None:
    project.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    applied(project, deltas={"search": delta(modified=(CHANGED,), added=(requirement("Order"),))})
    lifecycle.sync(project.root, NAME, LATER)
    record = project.record()
    assert record.problems == ()
    living = record.specs["search"]
    assert [item.name for item in living.requirements] == ["Result limit", "Empty query", "Order"]
    assert "twenty" in living.requirements[0].statement
    change = record.changes[NAME]
    assert change.proposal is not None
    assert change.proposal.synced == LATER
    assert change.proposal.acceptance is not None
    assert change.proposal.acceptance.date == DAY
    state = project.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert state.applied
    assert state.conflicts == ()
    with pytest.raises(Refusal, match="already synced"):
        lifecycle.sync(project.root, NAME, LATER)


def test_synced_change_archives_without_merging_again(project: Workspace) -> None:
    applied(project)
    lifecycle.sync(project.root, NAME, DAY)
    synced = project.read("specs/search.md")
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    assert project.read("specs/search.md") == synced
    record = project.record()
    assert record.problems == ()
    assert record.changes == {}


def test_synced_change_is_in_conflict_when_its_spec_moves_on(project: Workspace) -> None:
    applied(project)
    lifecycle.sync(project.root, NAME, DAY)
    project.replace("specs/search.md", "at most fifty", "at most thirty")
    state = project.change_state()
    assert [conflict.kind for conflict in state.conflicts] == [ConflictKind.MISMATCH]
    assert not state.applied
    with pytest.raises(Refusal):
        lifecycle.archive(project.root, NAME, LATER, outcome="Done.")


def test_sync_of_a_change_without_deltas_is_refused(project: Workspace) -> None:
    applied(project, proposal_text=proposal(impact="No spec changes."), deltas={})
    with pytest.raises(Refusal, match="nothing to sync"):
        lifecycle.sync(project.root, NAME, LATER)


def test_default_tasks_change_runs_from_accept_to_archive(project: Workspace) -> None:
    project.change(tasks=TASKS)
    lifecycle.accept(project.root, NAME, DAY)
    for number in ("1.1", "1.2"):
        lifecycle.tick(project.root, NAME, number)
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    lifecycle.archive(project.root, NAME, LATER, outcome="Done.")
    assert project.record().problems == ()

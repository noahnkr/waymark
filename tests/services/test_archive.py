"""Archiving and syncing: the archive gate, the merge, the move and the links."""

import datetime

import pytest

from tests.support import (
    GOAL_TEXT,
    NO_SPECS,
    TASKS,
    Workspace,
    delta,
    milestone,
    proposal,
    requirement,
    spec,
)
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
ONE_ITEM = HEAD + "- [ ] 1.1 Cap it\n  - **Verify:** a test\n  - **Criteria:** fifty at most\n"
CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def applied(project: Workspace, name: str = NAME, **options: object) -> Workspace:
    """A change that is accepted, built and reviewed."""
    project.change(name, tasks=ONE_ITEM, **options)  # type: ignore[arg-type]
    lifecycle.accept(project.root, name, DAY)
    lifecycle.tick(project.root, name, "1.1")
    lifecycle.self_review(project.root, name, "matches the criteria", DAY)
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
    done = lifecycle.archive(project.root, NAME, LATER, built="Capped at fifty.")
    assert ARCHIVED in done.message
    record = project.record()
    assert record.problems == ()
    assert record.changes == {}
    assert [(entry.date, entry.name) for entry in record.archived_changes] == [(LATER, NAME)]
    assert not project.path(f"changes/{NAME}").exists()
    created = record.specs["search"]
    assert created.purpose == "How search behaves."
    assert [item.name for item in created.requirements] == ["Result limit"]
    assert "## Outcome\n\n- **Built:** Capped at fifty.\n- **Differs:** none\n" in project.read(
        f"{ARCHIVED}/proposal.md"
    )
    assert project.path(f"{ARCHIVED}/tasks.md").is_file()
    assert project.path(f"{ARCHIVED}/specs/search.md").is_file()


def test_archiving_the_last_change_keeps_the_changes_folder(project: Workspace) -> None:
    """Scenario: Last change archived."""
    project.write("changes/.gitkeep", "")
    applied(project)
    lifecycle.archive(project.root, NAME, LATER, built="Capped at fifty.")
    assert project.read("changes/.gitkeep") == ""
    record = project.record()
    assert record.changes == {}
    assert record.problems == ()


def test_archive_merges_into_an_existing_spec(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    applied(project, deltas={"search": delta(modified=(CHANGED,))})
    lifecycle.archive(project.root, NAME, LATER, built="Lowered.")
    living = project.record().specs["search"]
    assert [item.name for item in living.requirements] == ["Result limit", "Empty query"]
    assert "twenty" in living.requirements[0].statement


def test_archive_is_refused_for_an_unaccepted_change_even_with_an_override(
    project: Workspace,
) -> None:
    project.change(tasks=ONE_ITEM.replace("- [ ]", "- [x]"))
    assert "not accepted" in refused(project, built="Done.")
    message = refused(project, built="Done.", override="no time")
    assert "not accepted" in message
    assert "can't be overridden" in message


def test_archive_is_refused_when_acceptance_was_withdrawn(project: Workspace) -> None:
    applied(project)
    project.replace(f"changes/{NAME}/proposal.md", "Paging.", "Paging and sorting.")
    assert "not accepted as it stands" in refused(project, built="Done.", override="no time")


def test_archive_is_refused_while_items_are_unticked_even_with_an_override(
    project: Workspace,
) -> None:
    project.change()
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "item 1.2 is not ticked" in refused(project, built="Done.")
    assert "can't be overridden" in refused(project, built="Done.", override="no time")


def test_not_reviewed(project: Workspace) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    message = refused(project, built="Done.")
    assert "missing the self review of the change" in message
    assert "--override" in message


def test_archive_override_passes_missing_reviews_and_records_the_reason(
    project: Workspace,
) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.archive(
        project.root, NAME, LATER, built="Shipped.", override="reviewed in the pull request"
    )
    assert project.read(f"{ARCHIVED}/proposal.md").endswith(
        "## Outcome\n\n- **Built:** Shipped.\n- **Differs:** none\n"
    )
    assert project.read(f"{ARCHIVED}/tasks.md").endswith(
        "- 2026-02-01 (override) by Sam Doe: reviewed in the pull request\n"
    )
    assert project.record().changes == {}


def test_archive_override_also_passes_a_failed_review(project: Workspace) -> None:
    project.change(tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "naming", DAY, items=["1.1"])
    assert "missing the independent review" in refused(project, built="Shipped.")
    lifecycle.archive(project.root, NAME, LATER, built="Shipped.", override="naming is fine")
    assert project.record().changes == {}


def test_archive_override_is_refused_when_there_is_nothing_to_override(
    project: Workspace,
) -> None:
    applied(project)
    assert "nothing to override" in refused(project, built="Done.", override="just in case")


def test_archive_is_refused_on_a_conflict_even_with_an_override(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    applied(project, deltas={"search": delta(added=(requirement("Result order"),))})
    project.write("specs/search.md", spec(requirement(), requirement("Result order")))
    state = project.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert state.next_step.kind is StepKind.RESOLVE_CONFLICT
    assert "conflict" in refused(project, built="Done.")
    assert "can't be overridden" in refused(project, built="Done.", override="no time")


def test_archive_needs_an_outcome(project: Workspace) -> None:
    applied(project)
    assert "--built" in refused(project)


def test_archive_uses_an_outcome_already_written_in_the_proposal(project: Workspace) -> None:
    applied(project)
    text = project.read(f"changes/{NAME}/proposal.md")
    project.write(
        f"changes/{NAME}/proposal.md",
        text + "\n## Outcome\n\n- **Built:** Written by hand.\n- **Differs:** none\n",
    )
    assert "already has an outcome" in refused(project, built="Another.")
    lifecycle.archive(project.root, NAME, LATER)
    assert "Written by hand." in project.read(f"{ARCHIVED}/proposal.md")


def test_scenario_archived_with_an_outcome(project: Workspace) -> None:
    applied(project)
    lifecycle.archive(
        project.root, NAME, LATER, built="The result limit.", differs="Fifty, not twenty."
    )
    text = project.read(f"{ARCHIVED}/proposal.md")
    assert text.endswith(
        "## Outcome\n\n- **Built:** The result limit.\n- **Differs:** Fifty, not twenty.\n"
    )


def test_scenario_nothing_differs(project: Workspace) -> None:
    applied(project)
    lifecycle.archive(project.root, NAME, LATER, built="The result limit.")
    assert project.read(f"{ARCHIVED}/proposal.md").endswith("- **Differs:** none\n")


def test_differs_needs_built(project: Workspace) -> None:
    applied(project)
    assert "--differs goes with --built" in refused(project, differs="Fifty.")


def test_hand_written_outcome_needs_both_lines(project: Workspace) -> None:
    applied(project)
    text = project.read(f"changes/{NAME}/proposal.md")
    project.write(f"changes/{NAME}/proposal.md", text + "\n## Outcome\n\nWritten by hand.\n")
    message = refused(project)
    assert '"- **Built:**"' in message
    assert "- **Differs:** <how it differs, or none>" in message


def test_archive_of_the_same_name_twice_in_a_day_is_refused(project: Workspace) -> None:
    applied(project)
    project.write(f"{ARCHIVED}/proposal.md", proposal(outcome="Earlier."))
    assert "already archived today" in refused(project, built="Done.")


def test_archived_name_can_be_reused(project: Workspace) -> None:
    applied(project)
    lifecycle.archive(project.root, NAME, DAY, built="First.")
    project.change(tasks=ONE_ITEM, deltas={"search": delta(modified=(CHANGED,))})
    lifecycle.accept(project.root, NAME, LATER)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "fine", LATER)
    lifecycle.archive(project.root, NAME, LATER, built="Second.")
    record = project.record()
    assert [entry.date for entry in record.archived_changes] == [DAY, LATER]
    assert record.problems == ()


def exploration(status: str, context: str = "") -> str:
    return (
        f"# Paging\n\n- **Status:** {status}\n\n## Context\n\n{context}\n\n"
        "## Questions\n\n## Approaches\n\n## Conclusion\n\n## Related\n"
    )


def test_archive_rewrites_links_that_point_into_the_moved_folder(project: Workspace) -> None:
    applied(project)
    project.change("add-order")
    project.write(
        "explorations/paging.md",
        "# Paging\n\n- **Status:** led-to [add-limit](../changes/add-limit/), "
        "[add-order](../changes/add-order/proposal.md)\n\n"
        "## Context\n\nSee the [tasks](../changes/add-limit/tasks.md#limit).\n\n"
        "## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\n[add-limit](../changes/add-limit/)\n\n## Related\n",
    )
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    text = project.read("explorations/paging.md")
    assert f"[tasks](../{ARCHIVED}/tasks.md#limit)" in text
    assert f"[add-limit](../{ARCHIVED}/)" in text
    record = project.record()
    assert link_problems(record) == ()
    state = project.state().explorations["paging"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, "change add-limit")


def test_scenario_its_only_change_archived(project: Workspace) -> None:
    applied(project)
    project.write("specs/export.md", spec(title="Export"))
    project.write(
        "explorations/paging.md",
        exploration(
            "led-to [add-limit](../changes/add-limit/proposal.md)",
            "See [export](../specs/export.md).",
        ),
    )
    done = lifecycle.archive(project.root, NAME, LATER, built="Done.")
    moved = "explorations/archive/2026-02-01-paging.md"
    assert moved in done.paths
    assert not project.path("explorations/paging.md").exists()
    assert project.read(moved) == exploration(
        f"led-to [add-limit](../../{ARCHIVED}/proposal.md)",
        "See [export](../../specs/export.md).",
    )
    record = project.record()
    assert record.problems == ()
    assert record.explorations == {}
    assert [(entry.date, entry.name, entry.path) for entry in record.archived_explorations] == [
        (LATER, "paging", moved)
    ]
    assert link_problems(record) == ()


def test_archived_change_follows_its_exploration_to_the_archive(project: Workspace) -> None:
    """The archived change's own link to the exploration it came from is re-aimed too."""
    link = "From [paging](../../explorations/paging.md).\n\n"
    applied(project, proposal_text=proposal().replace("## Why\n\n", f"## Why\n\n{link}", 1))
    project.write(
        "explorations/paging.md",
        exploration("led-to [add-limit](../changes/add-limit/proposal.md)"),
    )
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    archived = project.read(f"{ARCHIVED}/proposal.md")
    assert "[paging](../../../explorations/archive/2026-02-01-paging.md)" in archived
    assert project.path("explorations/archive/2026-02-01-paging.md").is_file()


def test_scenario_one_of_two_changes_archived(project: Workspace) -> None:
    applied(project)
    project.change("add-page-cursor")
    project.write(
        "explorations/paging.md",
        exploration(
            "led-to [add-limit](../changes/add-limit/proposal.md), "
            "[add-page-cursor](../changes/add-page-cursor/proposal.md)"
        ),
    )
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    assert project.read("explorations/paging.md") == exploration(
        f"led-to [add-limit](../{ARCHIVED}/proposal.md), "
        "[add-page-cursor](../changes/add-page-cursor/proposal.md)"
    )
    record = project.record()
    assert "paging" in record.explorations
    assert record.archived_explorations == ()
    assert link_problems(record) == ()


def test_scenario_change_in_a_milestone_the_exploration_led_to(project: Workspace) -> None:
    applied(project)
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [ ] [Limit](../../changes/add-limit/proposal.md)\n"),
    )
    status = "led-to [faster-search](../milestones/faster-search/milestone.md)"
    project.write("explorations/paging.md", exploration(status))
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    assert project.read("explorations/paging.md") == exploration(status)
    assert project.record().archived_explorations == ()


def test_archive_refused_when_an_exploration_of_the_name_was_archived_that_day(
    project: Workspace,
) -> None:
    applied(project)
    project.write(
        "explorations/paging.md",
        exploration("led-to [add-limit](../changes/add-limit/proposal.md)"),
    )
    project.write("explorations/archive/2026-02-01-paging.md", exploration("dropped"))
    message = refused(project, built="Done.")
    assert "explorations/archive/2026-02-01-paging.md" in message
    assert '"paging"' in message


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
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    text = project.read(f"{ARCHIVED}/design.md")
    assert "[export](../../../specs/export.md)" in text
    assert "[tasks](tasks.md)" in text
    assert "[readme](../../../../README.md)" in text
    assert "[the web](https://example.com/a.md)" in text


def test_scenario_roadmap_ticked_at_archive(project: Workspace) -> None:
    applied(project)
    goal = GOAL_TEXT.replace("- P95 is low.", "- [ ] P95 is low.")
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [ ] [Limit](../../changes/add-limit/proposal.md)\n", goal=goal),
    )
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    text = project.read("milestones/faster-search/milestone.md")
    assert text == milestone(f"- [x] [Limit](../../{ARCHIVED}/proposal.md)\n", goal=goal)
    state = project.state().milestones["faster-search"]
    assert (state.archived, state.total) == (1, 1)
    assert [line.status for line in state.lines] == [RoadmapStatus.ARCHIVED]


def test_a_link_outside_the_roadmap_is_rewritten_but_not_ticked(project: Workspace) -> None:
    applied(project)
    goal = GOAL_TEXT.replace(
        "- P95 is low.", "- [ ] [Limit](../../changes/add-limit/proposal.md) ships"
    )
    project.write("milestones/faster-search/milestone.md", milestone("- [ ] Paging\n", goal=goal))
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    text = project.read("milestones/faster-search/milestone.md")
    assert f"- [ ] [Limit](../../{ARCHIVED}/proposal.md) ships" in text


def test_archive_ticks_the_roadmap_line_and_the_milestone_moves_on(project: Workspace) -> None:
    applied(project)
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [ ] [Limit](../../changes/add-limit/proposal.md)\n- [ ] Paging later\n"),
    )
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    assert project.read("milestones/faster-search/milestone.md") == milestone(
        f"- [x] [Limit](../../{ARCHIVED}/proposal.md)\n- [ ] Paging later\n"
    )
    state = project.state().milestones["faster-search"]
    assert [line.status for line in state.lines] == [
        RoadmapStatus.ARCHIVED,
        RoadmapStatus.PLANNED,
    ]
    assert (state.archived, state.total) == (1, 1)
    assert link_problems(project.record()) == ()


def test_archive_leaves_unrelated_files_untouched(project: Workspace) -> None:
    project.write("specs/export.md", spec(title="Export"))
    project.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    applied(project)
    before = snapshot(project)
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    after = snapshot(project)
    for path in ("charter.md", "config.toml", "specs/export.md", "changes/add-order/tasks.md"):
        assert after[path] == before[path]


def test_failed_archive_leaves_the_record_as_it_was(project: Workspace) -> None:
    applied(project)
    project.write("changes/archive", "a file where the archive folder should be\n")
    before = snapshot(project)
    with pytest.raises(Refusal, match="Nothing was changed"):
        lifecycle.archive(project.root, NAME, LATER, built="Done.")
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

    lifecycle.archive(project.root, "fix-limit", LATER, built="Twenty.")
    state = project.change_state("cut-limit")
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert state.phase is Phase.PLANNED
    with pytest.raises(Refusal, match="not accepted as it stands"):
        lifecycle.archive(project.root, "cut-limit", LATER, built="Ten.")
    assert "twenty" in project.read("specs/search.md")

    lifecycle.accept(project.root, "cut-limit", LATER)
    lifecycle.archive(project.root, "cut-limit", LATER, built="Ten.")
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
    assert change.synced == LATER
    assert change.acceptance is not None
    assert change.acceptance.date == DAY
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
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
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
        lifecycle.archive(project.root, NAME, LATER, built="Done.")


def test_sync_of_a_change_without_deltas_is_refused(project: Workspace) -> None:
    applied(project, proposal_text=proposal(impact=NO_SPECS), deltas={})
    with pytest.raises(Refusal, match="nothing to sync"):
        lifecycle.sync(project.root, NAME, LATER)


def test_default_tasks_change_runs_from_accept_to_archive(project: Workspace) -> None:
    project.change(tasks=TASKS)
    lifecycle.accept(project.root, NAME, DAY)
    for number in ("1.1", "1.2"):
        lifecycle.tick(project.root, NAME, number)
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    lifecycle.archive(project.root, NAME, LATER, built="Done.")
    assert project.record().problems == ()


def test_sync_keeps_the_items_the_acceptance_names(project: Workspace) -> None:
    project.change()
    lifecycle.accept(project.root, NAME, DAY)
    tasks = f"changes/{NAME}/tasks.md"
    project.replace(
        tasks,
        "\n## Log\n",
        "- [ ] 1.3 Announce it\n  - **Criteria:** done\n  - **Verify:** a test\n\n## Log\n",
    )
    for number in ("1.1", "1.2", "1.3"):
        lifecycle.tick(project.root, NAME, number)
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    lifecycle.sync(project.root, NAME, DAY)
    text = project.read(tasks)
    assert " items 1.1, 1.2 by " in text
    assert "- 2026-01-15 (synced) fingerprint " in text
    assert project.change_state(NAME).acceptance is AcceptanceState.VALID


def test_archiving_a_rename_renames_the_requirement_in_the_spec(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement("Result cap")))
    rename = (
        "# Search\n\n## RENAMED Requirements\n\n- **From:** Result cap\n- **To:** Result limit\n"
    )
    applied(project, deltas={"search": rename})
    lifecycle.archive(project.root, NAME, LATER, built="Renamed.")
    living = project.record().specs["search"]
    assert [item.name for item in living.requirements] == ["Result limit"]
    assert living.requirements[0].scenarios


def test_scenario_member_change_archived(project: Workspace) -> None:
    """Requirement "Milestone log": archiving a member change writes (archived)."""
    member = proposal().replace(
        "- **Owner:** Sam Doe\n", "- **Owner:** Sam Doe\n- **Milestone:** faster-search\n"
    )
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [ ] [add-limit](../../changes/add-limit/proposal.md): cap\n"),
    )
    applied(project, proposal_text=member)
    lifecycle.archive(project.root, NAME, LATER, built="Shipped.", by="Ada")
    text = project.read("milestones/faster-search/milestone.md")
    assert f"- [x] [add-limit](../../{ARCHIVED}/proposal.md): cap\n" in text
    assert text.endswith("\n## Log\n\n- 2026-02-01 (archived) add-limit by Ada\n")


def test_a_change_without_a_milestone_writes_no_milestone_record(project: Workspace) -> None:
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [ ] [add-limit](../../changes/add-limit/proposal.md): cap\n"),
    )
    applied(project)
    lifecycle.archive(project.root, NAME, LATER, built="Shipped.")
    assert "## Log" not in project.read("milestones/faster-search/milestone.md")

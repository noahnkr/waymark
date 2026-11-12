"""State derived from the files: phases, next steps, reviews, conflicts and progress."""

import shutil

from tests.support import DESIGN, TASKS, Workspace, delta, proposal, requirement, spec
from waymark.record.state import (
    AcceptanceState,
    ChangeState,
    ConflictKind,
    ExplorationStatus,
    RoadmapStatus,
    StepKind,
)
from waymark.record.terms import Phase, ReviewLevel

FOLDER = "changes/add-limit"
TASKS_FILE = f"{FOLDER}/tasks.md"
HEAD = "# Tasks\n\n## 1. Limit\n\n"
CHANGED = requirement(statement="A search SHALL return at most twenty results.")
SELF_REVIEW = "  - (self-review) 2026-01-16: matches the criteria\n"


def step(state: ChangeState) -> tuple[Phase, StepKind, str | None, bool]:
    return state.phase, state.next_step.kind, state.next_step.item, state.next_step.human


def with_tasks(workspace: Workspace, tasks: str, *, short: bool = False) -> ChangeState:
    """An accepted change with the given task list; evidence is added after acceptance."""
    bare = "\n".join(
        line.replace("- [x]", "- [ ]")
        for line in tasks.split("\n")
        if not line.strip().startswith(("- (", "- Blocked:"))
    )
    workspace.change(
        proposal_text=proposal(short=short), design=None if short else DESIGN, tasks=bare
    )
    workspace.accept()
    workspace.write(TASKS_FILE, tasks)
    state = workspace.change_state()
    assert state.acceptance is AcceptanceState.VALID
    return state


def code_list(workspace: Workspace) -> list[tuple[str, str]]:
    return [(problem.path, problem.code) for problem in workspace.record().problems]


def test_next_step_is_right_at_every_stop_on_the_full_path(workspace: Workspace) -> None:
    workspace.write(f"{FOLDER}/proposal.md", "# Limit the results\n\nOwner: Sam Doe\n")
    assert step(workspace.change_state()) == (Phase.PROPOSED, StepKind.PROPOSE, None, False)

    workspace.write(f"{FOLDER}/proposal.md", proposal())
    assert step(workspace.change_state()) == (Phase.PROPOSED, StepKind.SPECS, None, False)

    workspace.write(
        f"{FOLDER}/specs/search.md", delta(added=(requirement(),), purpose="How search behaves.")
    )
    assert step(workspace.change_state()) == (Phase.SPECIFIED, StepKind.DESIGN, None, False)

    workspace.write(f"{FOLDER}/design.md", DESIGN)
    assert step(workspace.change_state()) == (Phase.DESIGNED, StepKind.TASKS, None, False)

    workspace.write(TASKS_FILE, TASKS)
    assert step(workspace.change_state()) == (Phase.PLANNED, StepKind.ACCEPT, None, True)

    workspace.accept()
    assert step(workspace.change_state()) == (Phase.ACCEPTED, StepKind.APPLY, "1.1", False)

    workspace.replace(TASKS_FILE, "- [ ] 1.1", "- [x] 1.1")
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.REVIEW, "1.1", False)

    workspace.replace(TASKS_FILE, "fifty-one matches\n", "fifty-one matches\n" + SELF_REVIEW)
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)

    workspace.replace(TASKS_FILE, "- [ ] 1.2", "- [x] 1.2")
    state = workspace.change_state()
    assert step(state) == (Phase.APPLIED, StepKind.ARCHIVE, None, True)
    assert state.applied
    assert (state.ticked, state.total) == (2, 2)


def test_short_path_skips_the_designed_phase(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(short=True), design=None, tasks=None)
    state = workspace.change_state()
    assert state.short_path
    assert step(state) == (Phase.SPECIFIED, StepKind.TASKS, None, False)
    workspace.write(TASKS_FILE, TASKS)
    assert step(workspace.change_state()) == (Phase.PLANNED, StepKind.ACCEPT, None, True)


def test_full_path_needs_a_design_before_tasks(workspace: Workspace) -> None:
    workspace.change(design=None)
    assert step(workspace.change_state()) == (Phase.SPECIFIED, StepKind.DESIGN, None, False)


def test_short_path_change_with_a_design_is_a_problem(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(short=True))
    assert code_list(workspace) == [(f"{FOLDER}/design.md", "short-path-design")]
    assert workspace.change_state().next_step.kind is StepKind.DESIGN


def test_short_path_allows_no_independent_review(workspace: Workspace) -> None:
    tasks = TASKS.replace(
        "1.1 Cap the result count", "1.1 Cap the result count   `review: independent`"
    )
    workspace.change(proposal_text=proposal(short=True), design=None, tasks=tasks)
    assert code_list(workspace) == [(TASKS_FILE, "short-path-review")]
    assert workspace.change_state().next_step.kind is StepKind.TASKS


def test_change_with_no_spec_changes_is_specified_without_deltas(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(impact="No spec changes."), deltas={}, design=None)
    assert step(workspace.change_state()) == (Phase.SPECIFIED, StepKind.DESIGN, None, False)


def test_stating_no_spec_changes_while_having_deltas_is_a_problem(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(impact="No spec changes."))
    assert code_list(workspace) == [(f"{FOLDER}/proposal.md", "impact-mismatch")]
    assert workspace.change_state().next_step.kind is StepKind.PROPOSE


def test_artifact_with_format_problems_is_the_next_step(workspace: Workspace) -> None:
    workspace.change()
    workspace.replace(f"{FOLDER}/specs/search.md", "- WHEN a search runs\n", "")
    state = workspace.change_state()
    assert step(state) == (Phase.PROPOSED, StepKind.SPECS, None, False)
    assert "WHEN" in state.next_step.reason


def test_task_list_without_items_is_not_planned(workspace: Workspace) -> None:
    workspace.change(tasks="# Tasks\n\n## 1. Limit\n")
    assert step(workspace.change_state()) == (Phase.DESIGNED, StepKind.TASKS, None, False)


def test_owner_comes_from_the_proposal(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(owner="Robin Roe"))
    assert workspace.change_state().owner == "Robin Roe"


def test_items_of_an_unaccepted_change_are_not_next(workspace: Workspace) -> None:
    workspace.change()
    assert workspace.change_state().next_step.kind is StepKind.ACCEPT


def test_withdrawn_acceptance_sends_the_change_back_to_accept(workspace: Workspace) -> None:
    workspace.change()
    workspace.accept()
    workspace.replace(TASKS_FILE, "- [ ] 1.1", "- [x] 1.1")
    workspace.replace(f"{FOLDER}/proposal.md", "Paging.", "Paging and sorting.")
    state = workspace.change_state()
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert step(state) == (Phase.PLANNED, StepKind.ACCEPT, None, True)
    assert "edited after it was accepted" in state.next_step.reason
    assert not state.applied


def test_progress_is_ticked_items_out_of_all_items(workspace: Workspace) -> None:
    state = with_tasks(workspace, HEAD + "- [x] 1.1 A\n- [ ] 1.2 B\n- [x] 1.3 C\n")
    assert (state.ticked, state.total) == (2, 3)


def test_item_at_level_none_needs_no_review_record(workspace: Workspace) -> None:
    state = with_tasks(workspace, HEAD + "- [x] 1.1 Rename a file   `review: none`\n")
    assert state.items[0].reviewed
    assert step(state) == (Phase.APPLIED, StepKind.ARCHIVE, None, True)


def test_item_at_level_self_needs_a_self_review_record(workspace: Workspace) -> None:
    state = with_tasks(workspace, HEAD + "- [x] 1.1 Cap it\n")
    assert not state.items[0].reviewed
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, "1.1", False)
    shutil.rmtree(workspace.path(FOLDER))
    state = with_tasks(workspace, HEAD + "- [x] 1.1 Cap it\n" + SELF_REVIEW)
    assert state.items[0].reviewed
    assert state.applied


def test_item_at_level_independent_needs_a_passing_review(workspace: Workspace) -> None:
    item = "- [x] 1.1 Cap it   `review: independent`\n"
    state = with_tasks(workspace, HEAD + item + SELF_REVIEW)
    assert state.items[0].level is ReviewLevel.INDEPENDENT
    assert not state.items[0].reviewed
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, "1.1", False)
    shutil.rmtree(workspace.path(FOLDER))
    state = with_tasks(workspace, HEAD + item + "  - (review) 2026-01-16 pass: boundary covered\n")
    assert state.items[0].reviewed
    assert state.applied


def test_unticked_item_is_never_reviewed(workspace: Workspace) -> None:
    state = with_tasks(workspace, HEAD + "- [ ] 1.1 Cap it\n" + SELF_REVIEW)
    assert not state.items[0].reviewed
    assert step(state) == (Phase.ACCEPTED, StepKind.APPLY, "1.1", False)


def test_changes_verdict_sends_the_item_back_to_apply(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD + "- [x] 1.1 Cap it   `review: independent`\n"
        "  - (review) 2026-01-16 changes: off by one\n- [ ] 1.2 Next\n",
    )
    assert state.items[0].redo
    assert not state.items[0].reviewed
    assert step(state) == (Phase.APPLYING, StepKind.APPLY, "1.1", False)
    assert "Reopen" in state.next_step.reason


def test_reopened_item_is_applied_again_then_reviewed_independently(workspace: Workspace) -> None:
    records = "  - (review) 2026-01-16 changes: off by one\n  - (reopened) 2026-01-17\n"
    state = with_tasks(workspace, HEAD + "- [ ] 1.1 Cap it\n" + records)
    assert step(state) == (Phase.ACCEPTED, StepKind.APPLY, "1.1", False)
    assert not state.items[0].redo

    workspace.replace(TASKS_FILE, "- [ ] 1.1", "- [x] 1.1")
    state = workspace.change_state()
    assert state.items[0].level is ReviewLevel.INDEPENDENT
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, "1.1", False)

    workspace.write(TASKS_FILE, workspace.read(TASKS_FILE) + SELF_REVIEW)
    assert not workspace.change_state().items[0].reviewed

    workspace.replace(TASKS_FILE, SELF_REVIEW, "  - (review) 2026-01-18 pass: fixed\n")
    assert workspace.change_state().applied


def test_second_changes_verdict_goes_to_the_human(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD + "- [x] 1.1 Cap it\n"
        "  - (review) 2026-01-16 changes: off by one\n"
        "  - (reopened) 2026-01-17\n"
        "  - (review) 2026-01-18 changes: still off by one\n",
    )
    assert state.items[0].escalated == "a second review asked for changes: still off by one"
    assert step(state) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, "1.1", True)


def test_spec_gap_verdict_goes_to_the_human(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD + "- [x] 1.1 Cap it\n  - (review) 2026-01-16 spec-gap: no scenario for zero results\n"
        "- [ ] 1.2 Next\n",
    )
    assert state.items[0].escalated == (
        "the reviewer found a spec gap: no scenario for zero results"
    )
    assert step(state) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)
    workspace.replace(TASKS_FILE, "- [ ] 1.2 Next\n", "- [x] 1.2 Next\n" + SELF_REVIEW)
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, "1.1", True)


def test_blocked_item_is_skipped_until_only_blocked_items_remain(workspace: Workspace) -> None:
    state = with_tasks(
        workspace, HEAD + "- [ ] 1.1 Cap it\n  - Blocked: waiting for wording\n- [ ] 1.2 Next\n"
    )
    assert state.items[0].blocked == "waiting for wording"
    assert step(state) == (Phase.ACCEPTED, StepKind.APPLY, "1.2", False)
    workspace.replace(TASKS_FILE, "- [ ] 1.2 Next\n", "- [x] 1.2 Next\n" + SELF_REVIEW)
    state = workspace.change_state()
    assert step(state) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, "1.1", True)
    assert state.next_step.reason == "blocked: waiting for wording"
    assert not state.applied


def test_delta_that_no_longer_matches_its_spec_is_a_conflict(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    workspace.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    workspace.accept("fix-limit")
    assert workspace.change_state("fix-limit").conflicts == ()

    workspace.write("specs/search.md", spec(requirement("Result cap")))
    state = workspace.change_state("fix-limit")
    (conflict,) = state.conflicts
    assert conflict.kind is ConflictKind.MISMATCH
    assert conflict.domain == "search"
    assert state.next_step.kind is StepKind.RESOLVE_CONFLICT
    assert "Result limit" in state.next_step.reason


def test_change_with_a_mismatch_is_not_applied(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    tasks = HEAD + "- [ ] 1.1 Cap it   `review: none`\n"
    workspace.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))}, tasks=tasks)
    workspace.accept("fix-limit")
    workspace.replace("changes/fix-limit/tasks.md", "- [ ]", "- [x]")
    assert workspace.change_state("fix-limit").applied

    removal = delta(removed=(("Result limit", "Dropped."),), added=(requirement("Result cap"),))
    workspace.write("changes/fix-limit/specs/search.md", removal)
    workspace.accept("fix-limit")
    workspace.write("specs/search.md", spec(requirement("Result cap")))
    state = workspace.change_state("fix-limit")
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert not state.applied
    assert state.next_step.kind is StepKind.RESOLVE_CONFLICT


def test_added_requirement_already_in_the_spec_is_a_conflict(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    workspace.change(deltas={"search": delta(added=(requirement(),))})
    (conflict,) = workspace.change_state().conflicts
    assert conflict.kind is ConflictKind.MISMATCH


def test_two_changes_touching_the_same_requirement_overlap(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    workspace.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    workspace.change("drop-limit", deltas={"search": delta(removed=(("result LIMIT", "Unused."),))})
    workspace.change("fix-empty", deltas={"search": delta(modified=(requirement("Empty query"),))})
    state = workspace.state()
    (overlap,) = state.overlaps
    assert overlap.kind is ConflictKind.OVERLAP
    assert (overlap.domain, overlap.changes) == ("search", ("drop-limit", "fix-limit"))
    assert state.changes["fix-limit"].conflicts == (overlap,)
    assert state.changes["drop-limit"].conflicts == (overlap,)
    assert state.changes["fix-empty"].conflicts == ()


def test_overlap_blocks_neither_change(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    tasks = HEAD + "- [x] 1.1 Cap it   `review: none`\n"
    for name, limit in (("fix-limit", "twenty"), ("cut-limit", "ten")):
        changed = requirement(statement=f"A search SHALL return at most {limit} results.")
        workspace.change(name, deltas={"search": delta(modified=(changed,))}, tasks=tasks)
        workspace.accept(name)
    state = workspace.state()
    assert len(state.overlaps) == 1
    assert state.changes["fix-limit"].applied
    assert state.changes["cut-limit"].applied


def test_changes_in_different_specs_or_requirements_do_not_overlap(workspace: Workspace) -> None:
    workspace.change("add-limit")
    workspace.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    workspace.change(
        "add-export",
        deltas={
            "export": delta(title="Export", added=(requirement(),), purpose="How export works.")
        },
    )
    assert workspace.state().overlaps == ()


def test_item_in_an_atlas_names_a_configured_repo(atlas: Workspace) -> None:
    atlas.change(
        tasks=HEAD
        + "- [ ] 1.1 Cap it\n- [ ] 1.2 Show it\n  - Repo: docs\n- [ ] 1.3 Ok\n  - Repo: api\n"
    )
    assert code_list(atlas) == [
        (TASKS_FILE, "item-without-repo"),
        (TASKS_FILE, "unknown-repo"),
    ]
    assert atlas.change_state().next_step.kind is StepKind.TASKS


def test_change_can_span_the_repos_of_an_atlas(atlas: Workspace) -> None:
    atlas.change(
        tasks=HEAD + "- [ ] 1.1 Add the endpoint\n  - Repo: api\n- [ ] 1.2 Show it\n  - Repo: web\n"
    )
    assert atlas.record().problems == ()
    assert step(atlas.change_state()) == (Phase.PLANNED, StepKind.ACCEPT, None, True)


def test_repo_line_outside_an_atlas_is_a_problem(workspace: Workspace) -> None:
    workspace.change(tasks=HEAD + "- [ ] 1.1 Cap it\n  - Repo: api\n")
    assert code_list(workspace) == [(TASKS_FILE, "unknown-repo")]


def test_spec_and_delta_repos_must_be_configured(atlas: Workspace) -> None:
    atlas.write("specs/search.md", spec().replace("# Search\n", "# Search\n\nRepos: api, docs\n"))
    assert code_list(atlas) == [("specs/search.md", "unknown-repo")]


def test_milestone_progress_follows_its_roadmap_links(workspace: Workspace) -> None:
    workspace.change("add-order")
    workspace.write("changes/archive/2026-01-20-add-limit/proposal.md", proposal(outcome="Done."))
    workspace.write(
        "milestones/faster-search/goal.md",
        "# G\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n",
    )
    workspace.write(
        "milestones/faster-search/roadmap.md",
        "# Roadmap\n\n"
        "- [x] [Limit](../../changes/archive/2026-01-20-add-limit/proposal.md)\n"
        "- [ ] [Order](../../changes/add-order/)\n"
        "- [ ] [Gone](../../changes/add-cache/proposal.md)\n"
        "- [x] [Lost](../../changes/archive/2026-01-21-add-index/)\n"
        "- [ ] Paging, not proposed yet\n",
    )
    milestone = workspace.state().milestones["faster-search"]
    assert [(line.change, line.status) for line in milestone.lines] == [
        ("add-limit", RoadmapStatus.ARCHIVED),
        ("add-order", RoadmapStatus.ACTIVE),
        ("add-cache", RoadmapStatus.MISSING),
        ("add-index", RoadmapStatus.MISSING),
        (None, RoadmapStatus.PLANNED),
    ]
    assert (milestone.archived, milestone.total) == (1, 4)


def explore(workspace: Workspace, name: str, conclusion: str) -> None:
    workspace.write(
        f"explorations/{name}.md",
        f"# T\n\n## Context\n\n## Questions\n\n## Approaches\n\n## Conclusion\n\n{conclusion}\n\n"
        "## Related\n",
    )


def test_exploration_state_comes_from_its_conclusion(workspace: Workspace) -> None:
    workspace.change("add-paging")
    workspace.write("milestones/faster-search/roadmap.md", "# Roadmap\n")
    workspace.write(
        "milestones/faster-search/goal.md",
        "# G\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n",
    )
    explore(workspace, "caching", "")
    explore(workspace, "ranking", "Parked: nobody asked for it")
    explore(workspace, "paging", "See [add-paging](../changes/add-paging/proposal.md).")
    explore(workspace, "speed", "[Faster search](../milestones/faster-search/goal.md)")
    explore(workspace, "old", "[done](../changes/archive/2026-01-20-add-limit/proposal.md)")
    explore(workspace, "vague", "We should think about it more.")
    states = workspace.state().explorations
    assert {
        name: (state.status, state.detail) for name, state in states.items() if name != "vague"
    } == {
        "caching": (ExplorationStatus.OPEN, None),
        "ranking": (ExplorationStatus.PARKED, "nobody asked for it"),
        "paging": (ExplorationStatus.LED_TO, "change add-paging"),
        "speed": (ExplorationStatus.LED_TO, "milestone faster-search"),
        "old": (ExplorationStatus.LED_TO, "change add-limit"),
    }
    assert states["vague"].status is ExplorationStatus.UNREADABLE


def test_same_files_give_the_same_state(workspace: Workspace, atlas: Workspace) -> None:
    for space in (workspace, atlas):
        space.write("specs/search.md", spec())
        space.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
        space.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    assert workspace.state() == workspace.state()
    copy = Workspace(workspace.root.parent / "elsewhere" / "clone")
    shutil.copytree(workspace.path(""), copy.path(""), dirs_exist_ok=True)
    assert copy.state() == workspace.state()
    assert copy.record().problems == workspace.record().problems

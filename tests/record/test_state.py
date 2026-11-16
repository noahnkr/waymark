"""State derived from the files: phases, next steps, reviews, conflicts and progress."""

import shutil

from tests.support import (
    DESIGN,
    NO_SPECS,
    TASKS,
    Workspace,
    delta,
    milestone,
    proposal,
    requirement,
    spec,
)
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
REVIEW = "\n## Log\n\n"
SELF_REVIEW = REVIEW + "- (self-review) 2026-01-16: matches the criteria\n"


def reviewed_at(level: str, *, short: bool = False) -> str:
    """A proposal with a Review line."""
    facts = "Owner: Sam Doe\n" + ("Path: short\n" if short else "")
    return proposal(short=short).replace(facts, facts + f"- Review: {level}\n")


def step(state: ChangeState) -> tuple[Phase, StepKind, str | None, bool]:
    return state.phase, state.next_step.kind, state.next_step.item, state.next_step.human


def with_tasks(
    workspace: Workspace, tasks: str, *, short: bool = False, level: str | None = None
) -> ChangeState:
    """An accepted change with the given task list; evidence is added after acceptance."""
    bare = "\n".join(
        line.replace("- [x]", "- [ ]")
        for line in tasks.split("\n")
        if not line.strip().startswith(("- (", "- critical", "- warning"))
    )
    text = reviewed_at(level, short=short) if level else proposal(short=short)
    workspace.change(proposal_text=text, design=None if short else DESIGN, tasks=bare)
    workspace.accept()
    workspace.write_tasks(tasks)
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
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)

    workspace.replace(TASKS_FILE, "- [ ] 1.2", "- [x] 1.2")
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.REVIEW, None, False)

    record_line = SELF_REVIEW.removeprefix(REVIEW)
    workspace.write(TASKS_FILE, workspace.read(TASKS_FILE) + record_line)
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


def test_unsettled_design_keeps_the_next_step_at_design(workspace: Workspace) -> None:
    design = DESIGN.replace("- Status: decided", "- Status: proposed").replace(
        "None.", "- Fifty or twenty?"
    )
    workspace.change(design=design)
    state = workspace.change_state()
    assert (state.phase, state.next_step.kind) == (Phase.SPECIFIED, StepKind.DESIGN)
    assert state.next_step.reason == (
        'Settle the design before it is accepted: decision "Where to cut" is proposed; '
        'open question "Fifty or twenty?" is listed.'
    )


def test_full_path_without_a_design(workspace: Workspace) -> None:
    workspace.change(design=None)
    assert step(workspace.change_state()) == (Phase.SPECIFIED, StepKind.DESIGN, None, False)


def test_design_on_the_short_path(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(short=True))
    assert code_list(workspace) == [(f"{FOLDER}/design.md", "short-path-design")]
    assert workspace.change_state().next_step.kind is StepKind.DESIGN


def test_short_path_allows_no_independent_review(workspace: Workspace) -> None:
    text = proposal(short=True).replace("Path: short\n", "Path: short\n- Review: independent\n")
    workspace.change(proposal_text=text, design=None)
    assert code_list(workspace) == [(f"{FOLDER}/proposal.md", "short-path-review")]


def test_short_path_takes_an_independent_project_default_as_a_problem(
    workspace: Workspace,
) -> None:
    workspace.replace("config.toml", 'default_review = "self"', 'default_review = "independent"')
    workspace.change(proposal_text=proposal(short=True), design=None)
    assert code_list(workspace) == [(f"{FOLDER}/proposal.md", "short-path-review")]


def test_review_level_comes_from_the_proposal_or_the_project_default(
    workspace: Workspace,
) -> None:
    workspace.change()
    change = workspace.record().changes["add-limit"]
    assert change.review_level(ReviewLevel.NONE) is ReviewLevel.NONE
    text = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: independent\n")
    workspace.change(proposal_text=text)
    change = workspace.record().changes["add-limit"]
    assert change.review_level(ReviewLevel.NONE) is ReviewLevel.INDEPENDENT


def test_old_tag(workspace: Workspace) -> None:
    tasks = TASKS.replace(
        "1.1 Cap the result count", "1.1 Cap the result count   `review: independent`"
    )
    workspace.change(tasks=tasks)
    assert code_list(workspace) == [(TASKS_FILE, "old-record-format")]
    (problem,) = workspace.record().changes["add-limit"].problems
    assert "wm update" in problem.message


def test_change_with_no_spec_changes_is_specified_without_deltas(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(impact=NO_SPECS), deltas={}, design=None)
    assert step(workspace.change_state()) == (Phase.SPECIFIED, StepKind.DESIGN, None, False)


def test_stating_no_spec_changes_while_having_deltas_is_a_problem(workspace: Workspace) -> None:
    workspace.change(proposal_text=proposal(impact=NO_SPECS))
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
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [x] 1.1 A\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [ ] 1.2 B\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [x] 1.3 C\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        ),
    )
    assert (state.ticked, state.total) == (2, 3)


def test_change_at_level_none_needs_no_review(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD + "- [x] 1.1 Rename a file\n  - Criteria: done\n  - Verify: a test\n",
        level="none",
    )
    assert state.review.reviewed
    assert step(state) == (Phase.APPLIED, StepKind.ARCHIVE, None, True)


def test_all_items_ticked(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [x] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [x] 1.2 Tidy up\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        ),
    )
    assert state.review.level is ReviewLevel.SELF
    assert not state.review.reviewed
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, None, False)
    assert state.next_step.reason == "Review level: self."
    shutil.rmtree(workspace.path(FOLDER))
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [x] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [x] 1.2 Tidy up\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        )
        + SELF_REVIEW,
    )
    assert state.review.reviewed
    assert state.applied


def test_an_item_still_to_build(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [x] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [ ] 1.2 Tidy up\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        ),
    )
    assert step(state) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [x] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [ ] 1.2 Tidy up\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        )
        + SELF_REVIEW,
    )
    assert not state.review.reviewed


def test_independent_change_needs_a_passing_review(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n" + SELF_REVIEW,
        level="independent",
    )
    assert state.review.level is ReviewLevel.INDEPENDENT
    assert not state.review.reviewed
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, None, False)
    shutil.rmtree(workspace.path(FOLDER))
    state = with_tasks(
        workspace,
        HEAD
        + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n"
        + REVIEW
        + "- (review) 2026-01-16 pass: boundary covered\n",
        level="independent",
    )
    assert state.review.reviewed
    assert state.applied


def test_two_items_named(workspace: Workspace) -> None:
    items = HEAD + (
        "- [x] 1.1 Cap it\n"
        "  - Criteria: done\n"
        "  - Verify: a test\n"
        "- [x] 1.2 Page it\n"
        "  - Criteria: done\n"
        "  - Verify: a test\n"
        "\n"
        "## 2. Docs\n"
        "\n"
        "- [x] 2.1 Explain\n"
        "  - Criteria: done\n"
        "  - Verify: a test\n"
    )
    verdict = REVIEW + "- (review) 2026-01-16 changes 1.2 2.1: off by one\n"
    state = with_tasks(workspace, items + verdict)
    assert state.review.reopen == ("1.2", "2.1")
    assert [item.redo for item in state.items] == [False, True, True]
    assert step(state) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)
    assert "Reopen" in state.next_step.reason

    workspace.replace(
        TASKS_FILE,
        "- [x] 1.2 Page it\n  - Criteria: done\n  - Verify: a test\n",
        "- [ ] 1.2 Page it\n  - Criteria: done\n  - Verify: a test\n  - (reopened) 2026-01-17\n",
    )
    state = workspace.change_state()
    assert state.review.reopen == ("2.1",)
    assert step(state) == (Phase.APPLYING, StepKind.APPLY, "2.1", False)

    workspace.replace(
        TASKS_FILE,
        "- [x] 2.1 Explain\n  - Criteria: done\n  - Verify: a test\n",
        "- [ ] 2.1 Explain\n  - Criteria: done\n  - Verify: a test\n  - (reopened) 2026-01-17\n",
    )
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.APPLY, "1.2", False)

    workspace.replace(TASKS_FILE, "- [ ] 1.2", "- [x] 1.2")
    workspace.replace(TASKS_FILE, "- [ ] 2.1", "- [x] 2.1")
    state = workspace.change_state()
    assert state.review.level is ReviewLevel.INDEPENDENT
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, None, False)

    workspace.write(TASKS_FILE, workspace.read(TASKS_FILE) + "- (self-review) 2026-01-18: fixed\n")
    assert not workspace.change_state().review.reviewed
    workspace.write(TASKS_FILE, workspace.read(TASKS_FILE) + "- (review) 2026-01-18 pass: fixed\n")
    assert workspace.change_state().applied


def test_second_request_for_changes(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n  - (reopened) 2026-01-17\n"
        + REVIEW
        + "- (review) 2026-01-16 changes 1.1: off by one\n"
        + "- (review) 2026-01-18 changes 1.1: still off by one\n",
    )
    assert state.review.escalated == "a second review asked for changes: still off by one"
    assert state.review.reopen == ()
    assert step(state) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, None, True)

    workspace.write(TASKS_FILE, workspace.read(TASKS_FILE) + "- (resolved) 2026-01-19: keep it\n")
    state = workspace.change_state()
    assert state.review.escalated is None
    assert state.review.reopen == ()
    assert step(state) == (Phase.APPLYING, StepKind.REVIEW, None, False)
    assert state.review.level is ReviewLevel.INDEPENDENT


def test_spec_gap_verdict_goes_to_the_human(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n"
        + REVIEW
        + "- (review) 2026-01-16 spec-gap: no scenario for zero results\n",
    )
    assert state.review.escalated == "the reviewer found a spec gap: no scenario for zero results"
    assert step(state) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, None, True)


def test_spec_gap_from_the_builder_goes_to_the_human(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [ ] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - (gap) 2026-01-16: no limit given\n"
            "- [ ] 1.2 Next\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        ),
    )
    assert state.items[0].escalated == "the builder found a spec gap: no limit given"
    assert step(state) == (Phase.ACCEPTED, StepKind.APPLY, "1.2", False)
    workspace.replace(
        TASKS_FILE,
        "- [ ] 1.2 Next\n  - Criteria: done\n  - Verify: a test\n",
        "- [x] 1.2 Next\n  - Criteria: done\n  - Verify: a test\n",
    )
    assert step(workspace.change_state()) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, "1.1", True)


def test_blocked_item_is_skipped_until_only_blocked_items_remain(workspace: Workspace) -> None:
    state = with_tasks(
        workspace,
        HEAD
        + (
            "- [ ] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - (blocked) 2026-01-16: waiting for wording\n"
            "- [ ] 1.2 Next\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
        ),
    )
    assert state.items[0].blocked == "waiting for wording"
    assert step(state) == (Phase.ACCEPTED, StepKind.APPLY, "1.2", False)
    workspace.replace(
        TASKS_FILE,
        "- [ ] 1.2 Next\n  - Criteria: done\n  - Verify: a test\n",
        "- [x] 1.2 Next\n  - Criteria: done\n  - Verify: a test\n",
    )
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
    tasks = HEAD + "- [ ] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n"
    workspace.change(
        "fix-limit",
        proposal_text=reviewed_at("none"),
        deltas={"search": delta(modified=(CHANGED,))},
        tasks=tasks,
    )
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
    tasks = HEAD + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n"
    for name, limit in (("fix-limit", "twenty"), ("cut-limit", "ten")):
        changed = requirement(statement=f"A search SHALL return at most {limit} results.")
        workspace.change(
            name,
            proposal_text=reviewed_at("none"),
            deltas={"search": delta(modified=(changed,))},
            tasks=tasks,
        )
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
        + (
            "- [ ] 1.1 Cap it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "- [ ] 1.2 Show it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - Repo: docs\n"
            "- [ ] 1.3 Ok\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - Repo: api\n"
        )
    )
    assert code_list(atlas) == [
        (TASKS_FILE, "item-without-repo"),
        (TASKS_FILE, "unknown-repo"),
    ]
    assert atlas.change_state().next_step.kind is StepKind.TASKS


def test_change_can_span_the_repos_of_an_atlas(atlas: Workspace) -> None:
    atlas.change(
        tasks=HEAD
        + (
            "- [ ] 1.1 Add the endpoint\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - Repo: api\n"
            "- [ ] 1.2 Show it\n"
            "  - Criteria: done\n"
            "  - Verify: a test\n"
            "  - Repo: web\n"
        )
    )
    assert atlas.record().problems == ()
    assert step(atlas.change_state()) == (Phase.PLANNED, StepKind.ACCEPT, None, True)


def test_repo_line_outside_an_atlas_is_a_problem(workspace: Workspace) -> None:
    workspace.change(
        tasks=HEAD + "- [ ] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n  - Repo: api\n"
    )
    assert code_list(workspace) == [(TASKS_FILE, "unknown-repo")]


def test_spec_and_delta_repos_must_be_configured(atlas: Workspace) -> None:
    atlas.write("specs/search.md", spec().replace("# Search\n", "# Search\n\nRepos: api, docs\n"))
    assert code_list(atlas) == [("specs/search.md", "unknown-repo")]


def test_milestone_progress_follows_its_roadmap_links(workspace: Workspace) -> None:
    workspace.change("add-order")
    workspace.write("changes/archive/2026-01-20-add-limit/proposal.md", proposal(outcome="Done."))
    workspace.write(
        "milestones/faster-search/milestone.md",
        milestone(
            "- [x] [Limit](../../changes/archive/2026-01-20-add-limit/proposal.md)\n"
            "- [ ] [Order](../../changes/add-order/)\n"
            "- [ ] [Gone](../../changes/add-cache/proposal.md)\n"
            "- [x] [Lost](../../changes/archive/2026-01-21-add-index/)\n"
            "- [ ] Paging, not proposed yet\n"
        ),
    )
    milestone_state = workspace.state().milestones["faster-search"]
    assert [(line.change, line.status) for line in milestone_state.lines] == [
        ("add-limit", RoadmapStatus.ARCHIVED),
        ("add-order", RoadmapStatus.ACTIVE),
        ("add-cache", RoadmapStatus.MISSING),
        ("add-index", RoadmapStatus.MISSING),
        (None, RoadmapStatus.PLANNED),
    ]
    assert (milestone_state.archived, milestone_state.total) == (1, 4)


def explore(workspace: Workspace, name: str, status: str, conclusion: str = "") -> None:
    workspace.write(
        f"explorations/{name}.md",
        f"# T\n\n- Status: {status}\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        f"## Conclusion\n\n{conclusion}\n\n## Related\n",
    )


def test_exploration_state_comes_from_its_status_line(workspace: Workspace) -> None:
    workspace.change("add-paging")
    workspace.write("milestones/faster-search/milestone.md", milestone())
    explore(workspace, "caching", "open")
    explore(workspace, "ranking", "parked", "nobody asked for it")
    explore(workspace, "paging", "led-to [add-paging](../changes/add-paging/proposal.md)")
    explore(workspace, "speed", "led-to [Faster search](../milestones/faster-search/milestone.md)")
    explore(workspace, "old", "led-to [done](../changes/archive/2026-01-20-add-limit/proposal.md)")
    explore(workspace, "vague", "open", "We should think about it more.")
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
    assert states["vague"].status is ExplorationStatus.OPEN


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


def test_rename_of_a_missing_requirement_is_a_conflict(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    rename = "# Search\n\n## RENAMED Requirements\n\n- From: Result cap\n- To: Result size\n"
    workspace.change("rename-cap", deltas={"search": rename})
    (conflict,) = workspace.change_state("rename-cap").conflicts
    assert conflict.kind is ConflictKind.MISMATCH
    assert "Result cap" in conflict.message

"""Acceptance and evidence: what the commands write, and what each gate refuses."""

import datetime

import pytest

from tests.conftest import git_init
from tests.support import DESIGN, TASKS, Workspace, delta, proposal, requirement, spec
from waymark.record.state import AcceptanceState, StepKind
from waymark.record.terms import Phase, ReviewLevel, Verdict
from waymark.services import lifecycle
from waymark.services.common import Refusal

NAME = "add-limit"
TASKS_FILE = f"changes/{NAME}/tasks.md"
PROPOSAL_FILE = f"changes/{NAME}/proposal.md"
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
INDEPENDENT = HEAD + "- [ ] 1.1 Cap it   `review: independent`\n  - Criteria: fifty at most\n"


def accepted(project: Workspace, tasks: str = TASKS) -> Workspace:
    project.change(tasks=tasks)
    lifecycle.accept(project.root, NAME, DAY)
    return project


def refused(project: Workspace, action: str, *arguments: object) -> str:
    before = project.read(TASKS_FILE)
    with pytest.raises(Refusal) as refusal:
        getattr(lifecycle, action)(project.root, NAME, *arguments)
    assert project.read(TASKS_FILE) == before
    return str(refusal.value)


def test_accept_writes_the_acceptance_line_with_date_and_person(project: Workspace) -> None:
    project.change()
    before = project.read(PROPOSAL_FILE).split("\n")
    done = lifecycle.accept(project.root, NAME, DAY)
    assert done.paths == (PROPOSAL_FILE,)
    after = project.read(PROPOSAL_FILE).split("\n")
    added = [line for line in after if line not in before]
    assert len(added) == 1
    assert added[0].startswith("Accepted: 2026-01-15 by Sam Doe (fingerprint: ")
    assert [line for line in after if line != added[0]] == before
    assert after.index(added[0]) == after.index("Owner: Sam Doe") + 1
    state = project.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert (state.phase, state.next_step.kind) == (Phase.ACCEPTED, StepKind.APPLY)
    assert project.record().problems == ()


def test_accept_is_refused_while_an_artifact_is_missing(project: Workspace) -> None:
    project.change(tasks=None)
    with pytest.raises(Refusal, match='next step is "tasks"'):
        lifecycle.accept(project.root, NAME, DAY)
    assert "Accepted:" not in project.read(PROPOSAL_FILE)


def test_accept_is_refused_while_an_artifact_has_format_problems(project: Workspace) -> None:
    project.change()
    project.replace(f"changes/{NAME}/specs/search.md", "- WHEN a search runs\n", "")
    with pytest.raises(Refusal, match="WHEN"):
        lifecycle.accept(project.root, NAME, DAY)


def test_accept_is_refused_while_a_delta_does_not_match_its_spec(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement("Result cap")))
    project.change(deltas={"search": delta(modified=(requirement(),))})
    with pytest.raises(Refusal, match="conflict to resolve"):
        lifecycle.accept(project.root, NAME, DAY)


def test_accept_needs_a_name_to_record(workspace: Workspace) -> None:
    git_init(workspace.root, name=None)
    workspace.change()
    with pytest.raises(Refusal, match=r"git config user\.name"):
        lifecycle.accept(workspace.root, NAME, DAY)


def test_accepting_an_accepted_change_changes_nothing(project: Workspace) -> None:
    accepted(project)
    before = project.read(PROPOSAL_FILE)
    done = lifecycle.accept(project.root, NAME, datetime.date(2026, 3, 1))
    assert done.paths == ()
    assert project.read(PROPOSAL_FILE) == before


def test_accepting_again_after_an_edit_replaces_the_acceptance_line(project: Workspace) -> None:
    accepted(project)
    project.replace(PROPOSAL_FILE, "Paging.", "Paging and sorting.")
    assert project.change_state().acceptance is AcceptanceState.WITHDRAWN
    lifecycle.accept(project.root, NAME, datetime.date(2026, 3, 1))
    text = project.read(PROPOSAL_FILE)
    assert text.count("Accepted:") == 1
    assert "Accepted: 2026-03-01 by Sam Doe" in text
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_accept_keeps_windows_line_endings(project: Workspace) -> None:
    project.change()
    project.write(PROPOSAL_FILE, project.read(PROPOSAL_FILE).replace("\n", "\r\n"))
    lifecycle.accept(project.root, NAME, DAY)
    text = project.read(PROPOSAL_FILE)
    assert "\n" not in text.replace("\r\n", "")
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_unknown_change_or_item_is_refused_with_the_known_ones(project: Workspace) -> None:
    accepted(project)
    with pytest.raises(Refusal, match="Active changes: add-limit"):
        lifecycle.tick(project.root, "add-order", "1.1")
    assert "Its items: 1.1, 1.2" in refused(project, "tick", "7.7")


def test_items_of_an_unaccepted_change_cannot_be_applied(project: Workspace) -> None:
    project.change()
    assert "is not accepted" in refused(project, "tick", "1.1")
    assert "is not accepted" in refused(project, "block", "1.1", "waiting")
    assert "is not accepted" in refused(project, "verdict", "1.1", Verdict.PASS, "fine", DAY)
    assert "is not accepted" in refused(project, "self_review", "1.1", "fine", DAY)


def test_items_of_a_change_whose_acceptance_was_withdrawn_cannot_be_applied(
    project: Workspace,
) -> None:
    accepted(project)
    project.replace(PROPOSAL_FILE, "Paging.", "Paging and sorting.")
    assert "was withdrawn" in refused(project, "tick", "1.1")


def test_tick_marks_the_item_and_changes_no_other_line(project: Workspace) -> None:
    accepted(project)
    before = project.read(TASKS_FILE)
    done = lifecycle.tick(project.root, NAME, "1.1")
    assert done.paths == (TASKS_FILE,)
    assert project.read(TASKS_FILE) == before.replace("- [ ] 1.1", "- [x] 1.1")
    state = project.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert (state.next_step.kind, state.next_step.item) == (StepKind.REVIEW, "1.1")
    assert "already ticked" in refused(project, "tick", "1.1")


def test_self_review_writes_a_record_under_the_item(project: Workspace) -> None:
    accepted(project)
    assert "isn't ticked" in refused(project, "self_review", "1.1", "fine", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "  matches the\n criteria ", DAY)
    lines = project.read(TASKS_FILE).split("\n")
    record_line = "  - (self-review) 2026-01-15: matches the criteria"
    assert (
        lines.index(record_line) == lines.index("- [ ] 1.2 Document the limit   `review: none`") - 1
    )
    assert project.record().problems == ()
    assert project.change_state().items[0].reviewed
    assert "already has the review record" in refused(project, "self_review", "1.1", "again", DAY)


def test_self_review_does_not_count_for_an_item_needing_independent_review(
    project: Workspace,
) -> None:
    accepted(project, INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "independent review" in refused(project, "self_review", "1.1", "fine", DAY)


def test_item_at_level_none_takes_no_self_review(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    lifecycle.tick(project.root, NAME, "1.2")
    assert "needs no review record" in refused(project, "self_review", "1.2", "fine", DAY)
    assert project.change_state().applied


def test_evidence_text_must_not_be_empty(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "written into the record" in refused(project, "self_review", "1.1", "  \n ", DAY)
    assert "written into the record" in refused(project, "block", "1.2", "")


def test_passing_verdict_counts_as_the_independent_review(project: Workspace) -> None:
    accepted(project, INDEPENDENT)
    assert "isn't ticked" in refused(project, "verdict", "1.1", Verdict.PASS, "fine", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.PASS, "boundary covered", DAY)
    assert "  - (review) 2026-01-15 pass: boundary covered" in project.read(TASKS_FILE)
    state = project.change_state()
    assert state.items[0].reviewed
    assert state.applied
    assert project.record().problems == ()


def test_changes_verdict_is_reopened_then_needs_an_independent_pass(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n")
    assert "nothing to reopen" in refused(project, "reopen", "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "off by one", DAY)
    assert "waiting to be dealt with" in refused(
        project, "verdict", "1.1", Verdict.PASS, "fine", DAY
    )

    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    text = project.read(TASKS_FILE)
    assert "- [ ] 1.1 Cap it" in text
    assert text.rstrip("\n").endswith("  - (reopened) 2026-01-15")
    state = project.change_state()
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.1")

    lifecycle.tick(project.root, NAME, "1.1")
    assert project.change_state().items[0].level is ReviewLevel.INDEPENDENT
    assert "independent review" in refused(project, "self_review", "1.1", "fine", DAY)
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.PASS, "fixed", DAY)
    assert project.change_state().applied
    assert project.record().problems == ()


def test_second_changes_verdict_waits_for_the_human_until_resolved(project: Workspace) -> None:
    accepted(project, INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "off by one", DAY)
    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "still off", DAY)
    state = project.change_state()
    assert (state.next_step.kind, state.next_step.human) == (StepKind.RESOLVE_ITEMS, True)
    assert "nothing to reopen" in refused(project, "reopen", "1.1", DAY)

    lifecycle.resolve(project.root, NAME, "1.1", "use an inclusive bound", DAY)
    text = project.read(TASKS_FILE)
    assert "- [ ] 1.1 Cap it" in text
    assert "  - (resolved) 2026-01-15: use an inclusive bound" in text
    state = project.change_state()
    assert state.items[0].escalated is None
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.1")

    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "nearly", DAY)
    state = project.change_state()
    assert state.items[0].redo
    assert state.items[0].escalated is None
    assert project.record().problems == ()


def test_reviewer_spec_gap_goes_to_the_human(project: Workspace) -> None:
    accepted(project, INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.SPEC_GAP, "no scenario for zero", DAY)
    state = project.change_state()
    assert state.next_step.human
    assert state.items[0].escalated == "the reviewer found a spec gap: no scenario for zero"
    lifecycle.resolve(project.root, NAME, "1.1", "zero results is an empty list", DAY)
    assert project.change_state().next_step.kind is StepKind.APPLY


def test_block_writes_a_blocked_line_and_stops_the_item(project: Workspace) -> None:
    accepted(project)
    lifecycle.block(project.root, NAME, "1.1", "waiting for the wording")
    lines = project.read(TASKS_FILE).split("\n")
    blocked = "  - Blocked: waiting for the wording"
    assert lines.index(blocked) == lines.index("  - Verify: a test covers fifty-one matches") + 1
    state = project.change_state()
    assert state.items[0].blocked == "waiting for the wording"
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.2")
    assert state.acceptance is AcceptanceState.VALID
    assert "waits on the human" in refused(project, "tick", "1.1")
    assert 'already has a "Blocked:" line' in refused(project, "block", "1.1", "again")


def test_resolve_clears_a_blocker_and_records_the_decision(project: Workspace) -> None:
    accepted(project)
    before = project.read(TASKS_FILE)
    assert "nothing to resolve" in refused(project, "resolve", "1.1", "fine", DAY)
    lifecycle.block(project.root, NAME, "1.1", "waiting for the wording")
    lifecycle.resolve(project.root, NAME, "1.1", "use the short wording", DAY)
    text = project.read(TASKS_FILE)
    assert "Blocked:" not in text
    assert text == before.replace(
        "fifty-one matches\n",
        "fifty-one matches\n  - (resolved) 2026-01-15: use the short wording\n",
    )
    state = project.change_state()
    assert state.items[0].blocked is None
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.1")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    assert project.change_state().items[0].reviewed


def test_spec_gap_from_an_implementer_goes_to_the_human(project: Workspace) -> None:
    accepted(project)
    lifecycle.report_gap(project.root, NAME, "1.1", "the limit for an empty query is not stated")
    assert "  - Spec gap: the limit for an empty query is not stated" in project.read(TASKS_FILE)
    assert project.record().problems == ()
    state = project.change_state()
    assert state.items[0].escalated == (
        "the implementer found a spec gap: the limit for an empty query is not stated"
    )
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.2")
    assert "waits on the human" in refused(project, "tick", "1.1")

    lifecycle.resolve(project.root, NAME, "1.1", "an empty query is refused", DAY)
    assert "Spec gap:" not in project.read(TASKS_FILE)
    assert project.change_state().next_step.item == "1.1"


def test_ticked_item_cannot_be_blocked(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "already ticked" in refused(project, "block", "1.1", "too late")
    assert "already ticked" in refused(project, "report_gap", "1.1", "too late")


def test_evidence_commands_keep_windows_line_endings(project: Workspace) -> None:
    accepted(project)
    project.write(TASKS_FILE, project.read(TASKS_FILE).replace("\n", "\r\n"))
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    lifecycle.block(project.root, NAME, "1.2", "waiting")
    lifecycle.resolve(project.root, NAME, "1.2", "go ahead", DAY)
    text = project.read(TASKS_FILE)
    assert "\n" not in text.replace("\r\n", "")
    assert project.record().problems == ()
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_evidence_is_appended_to_a_task_list_without_a_final_newline(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    assert (
        project.read(TASKS_FILE) == HEAD + "- [x] 1.1 Cap it\n  - (self-review) 2026-01-15: fine\n"
    )


def test_short_path_change_runs_with_two_approvals(project: Workspace) -> None:
    project.change(
        proposal_text=proposal(short=True, impact="No spec changes."),
        deltas={},
        design=None,
        tasks=HEAD + "- [ ] 1.1 Fix the typo   `review: none`\n  - Criteria: the word is right\n",
    )
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    assert project.change_state().applied
    lifecycle.archive(project.root, NAME, DAY, outcome="Typo fixed.")
    assert project.record().changes == {}
    assert DESIGN not in project.read(f"changes/archive/2026-01-15-{NAME}/proposal.md")

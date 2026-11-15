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
ONE_ITEM = HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n"
REVIEW = "\n## Review\n\n"


def reviewed_at(level: str) -> str:
    return proposal().replace("Owner: Sam Doe\n", f"Owner: Sam Doe\nReview: {level}\n")


def accepted(project: Workspace, tasks: str = TASKS, level: str | None = None) -> Workspace:
    project.change(tasks=tasks, proposal_text=reviewed_at(level) if level else None)
    lifecycle.accept(project.root, NAME, DAY)
    return project


def built(project: Workspace, tasks: str = TASKS, level: str | None = None) -> Workspace:
    """An accepted change with every item ticked, waiting for its review."""
    accepted(project, tasks, level)
    for item in project.record().changes[NAME].tasks.items:  # type: ignore[union-attr]
        lifecycle.tick(project.root, NAME, item.number)
    return project


def refused(project: Workspace, action: str, *arguments: object, **options: object) -> str:
    before = project.read(TASKS_FILE)
    with pytest.raises(Refusal) as refusal:
        getattr(lifecycle, action)(project.root, NAME, *arguments, **options)
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
    assert "is not accepted" in refused(project, "verdict", Verdict.PASS, "fine", DAY)
    assert "is not accepted" in refused(project, "self_review", "fine", DAY)


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
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.2")
    assert "already ticked" in refused(project, "tick", "1.1")


def test_self_review_with_a_finding(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "item 1.2 is not ticked" in refused(project, "self_review", "fine", DAY)
    lifecycle.tick(project.root, NAME, "1.2")
    lifecycle.self_review(
        project.root,
        NAME,
        "  matches the\n criteria ",
        DAY,
        findings=["warning: src/a.py:12: the name is vague"],
    )
    assert project.read(TASKS_FILE) == TASKS.replace("- [ ]", "- [x]") + REVIEW + (
        "- (self-review) 2026-01-15: matches the criteria\n"
        "  - warning: src/a.py:12: the name is vague\n"
    )
    assert project.record().problems == ()
    state = project.change_state()
    assert state.review.reviewed
    assert state.applied
    assert "already has the review it needs" in refused(project, "self_review", "again", DAY)


def test_self_review_with_a_critical_finding_is_refused(project: Workspace) -> None:
    built(project)
    message = refused(
        project, "self_review", "fine", DAY, findings=["critical: src/a.py: returns 51"]
    )
    assert "critical finding" in message


def test_finding_that_breaks_the_format_is_refused(project: Workspace) -> None:
    built(project)
    message = refused(project, "self_review", "fine", DAY, findings=["looks odd"])
    assert "<critical|warning|suggestion>: <place>: <text>" in message


def test_self_review_does_not_count_for_a_change_needing_independent_review(
    project: Workspace,
) -> None:
    built(project, level="independent")
    assert "independent review" in refused(project, "self_review", "fine", DAY)


def test_change_at_level_none_takes_no_self_review(project: Workspace) -> None:
    built(project, level="none")
    assert "needs no review record" in refused(project, "self_review", "fine", DAY)
    assert project.change_state().applied


def test_evidence_text_must_not_be_empty(project: Workspace) -> None:
    built(project)
    assert "written into the record" in refused(project, "self_review", "  \n ", DAY)


def test_pass_with_a_critical_finding(project: Workspace) -> None:
    built(project, level="independent")
    message = refused(
        project,
        "verdict",
        Verdict.PASS,
        "fine",
        DAY,
        findings=["critical: src/search.py:12: fifty-one results come back"],
    )
    assert "critical finding" in message


def test_passing_verdict_counts_as_the_independent_review(project: Workspace) -> None:
    accepted(project, ONE_ITEM, "independent")
    assert "item 1.1 is not ticked" in refused(project, "verdict", Verdict.PASS, "fine", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(
        project.root,
        NAME,
        Verdict.PASS,
        "boundary covered",
        DAY,
        findings=["suggestion: docs/search.md: say the limit"],
    )
    text = project.read(TASKS_FILE)
    assert text.endswith(
        "- (review) 2026-01-15 pass: boundary covered\n"
        "  - suggestion: docs/search.md: say the limit\n"
    )
    state = project.change_state()
    assert state.review.reviewed
    assert state.applied
    assert project.record().problems == ()


def test_changes_verdict_names_items_the_change_has(project: Workspace) -> None:
    built(project)
    assert "names the items to rebuild" in refused(
        project, "verdict", Verdict.CHANGES, "off by one", DAY
    )
    assert "9.9" in refused(project, "verdict", Verdict.CHANGES, "off by one", DAY, items=["9.9"])
    assert "Only a" in refused(project, "verdict", Verdict.PASS, "fine", DAY, items=["1.1"])


def test_changes_verdict_is_reopened_then_needs_an_independent_pass(project: Workspace) -> None:
    built(project)
    assert "nothing to reopen" in refused(project, "reopen", "1.1", DAY)
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "off by one", DAY, items=["1.1"])
    assert "- (review) 2026-01-15 changes 1.1: off by one" in project.read(TASKS_FILE)
    assert "wm reopen add-limit 1.1" in refused(project, "verdict", Verdict.PASS, "fine", DAY)
    assert "nothing to reopen" in refused(project, "reopen", "1.2", DAY)

    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    text = project.read(TASKS_FILE)
    assert "- [ ] 1.1 Cap the result count" in text
    assert "  - (reopened) 2026-01-15\n- [x] 1.2" in text
    state = project.change_state()
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.1")

    lifecycle.tick(project.root, NAME, "1.1")
    state = project.change_state()
    assert state.review.level is ReviewLevel.INDEPENDENT
    assert (state.next_step.kind, state.next_step.item) == (StepKind.REVIEW, None)
    assert "independent review" in refused(project, "self_review", "fine", DAY)
    lifecycle.verdict(project.root, NAME, Verdict.PASS, "fixed", DAY)
    assert project.change_state().applied
    assert project.record().problems == ()


def test_second_changes_verdict_waits_for_the_human_until_resolved(project: Workspace) -> None:
    built(project, ONE_ITEM, "independent")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "off by one", DAY, items=["1.1"])
    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "still off", DAY, items=["1.1"])
    state = project.change_state()
    assert (state.next_step.kind, state.next_step.human) == (StepKind.RESOLVE_ITEMS, True)
    assert "nothing to reopen" in refused(project, "reopen", "1.1", DAY)
    assert "waits on the human" in refused(project, "verdict", Verdict.PASS, "fine", DAY)

    lifecycle.resolve(project.root, NAME, "review", "use an inclusive bound", DAY)
    assert project.read(TASKS_FILE).endswith("- (resolved) 2026-01-15: use an inclusive bound\n")
    state = project.change_state()
    assert state.review.escalated is None
    assert (state.next_step.kind, state.next_step.item) == (StepKind.REVIEW, None)

    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "nearly", DAY, items=["1.1"])
    state = project.change_state()
    assert state.review.reopen == ("1.1",)
    assert state.review.escalated is None
    assert project.record().problems == ()


def test_reviewer_spec_gap_goes_to_the_human(project: Workspace) -> None:
    built(project, ONE_ITEM, "independent")
    lifecycle.verdict(project.root, NAME, Verdict.SPEC_GAP, "no scenario for zero", DAY)
    state = project.change_state()
    assert state.next_step.human
    assert state.review.escalated == "the reviewer found a spec gap: no scenario for zero"
    assert "nothing to resolve" in refused(project, "resolve", "1.1", "fine", DAY)
    lifecycle.resolve(project.root, NAME, "review", "zero results is an empty list", DAY)
    assert project.change_state().next_step.kind is StepKind.REVIEW


def test_resolve_review_is_refused_when_nothing_went_to_the_human(project: Workspace) -> None:
    built(project)
    assert "nothing to resolve" in refused(project, "resolve", "review", "fine", DAY)


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
    assert project.change_state().items[0].ticked


def test_spec_gap_from_an_implementer_goes_to_the_human(project: Workspace) -> None:
    accepted(project)
    lifecycle.report_gap(project.root, NAME, "1.1", "the limit for an empty query is not stated")
    assert "  - Spec gap: the limit for an empty query is not stated" in project.read(TASKS_FILE)
    assert project.record().problems == ()
    state = project.change_state()
    assert state.items[0].escalated == (
        "the builder found a spec gap: the limit for an empty query is not stated"
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
    lifecycle.block(project.root, NAME, "1.2", "waiting")
    lifecycle.resolve(project.root, NAME, "1.2", "go ahead", DAY)
    lifecycle.tick(project.root, NAME, "1.2")
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    text = project.read(TASKS_FILE)
    assert "\n" not in text.replace("\r\n", "")
    assert project.record().problems == ()
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_evidence_is_appended_to_a_task_list_without_a_final_newline(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    assert project.read(TASKS_FILE) == (
        HEAD + "- [x] 1.1 Cap it\n" + REVIEW + "- (self-review) 2026-01-15: fine\n"
    )


def test_short_path_change_runs_with_two_approvals(project: Workspace) -> None:
    short = proposal(short=True, impact="No spec changes.")
    project.change(
        proposal_text=short.replace("Path: short\n", "Path: short\nReview: none\n"),
        deltas={},
        design=None,
        tasks=HEAD + "- [ ] 1.1 Fix the typo\n  - Criteria: the word is right\n",
    )
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    assert project.change_state().applied
    lifecycle.archive(project.root, NAME, DAY, outcome="Typo fixed.")
    assert project.record().changes == {}
    assert DESIGN not in project.read(f"changes/archive/2026-01-15-{NAME}/proposal.md")

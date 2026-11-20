"""Requirement "Review of items added after a review": what a review covers, and the rest."""

import datetime

import pytest

from tests.support import TASKS, Workspace, proposal
from waymark.record.state import StepKind
from waymark.record.terms import Verdict
from waymark.services import lifecycle
from waymark.services.common import Refusal
from waymark.services.instructions import instructions

NAME = "add-limit"
TASKS_FILE = f"changes/{NAME}/tasks.md"
DAY = datetime.date(2026, 1, 15)
LATER = datetime.date(2026, 2, 1)
ADDED = (
    "  - **Verify:** read the help text\n"
    "- [ ] 1.3 Name the limit in the error\n  - **Build:** planner\n"
    "  - **Criteria:** the error names fifty\n"
    "  - **Verify:** a test reads the error\n"
)


def at(level: str) -> str:
    return proposal().replace("- **Review:** self\n", f"- **Review:** {level}\n")


def passed_then_added(project: Workspace, level: str = "independent") -> None:
    """Items 1.1 and 1.2 pass a review covering them; then item 1.3 is added and ticked."""
    project.change(proposal_text=at(level))
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.2", DAY)
    if level == "self":
        lifecycle.self_review(project.root, NAME, "fine", DAY)
    else:
        lifecycle.verdict(project.root, NAME, Verdict.PASS, "fine", DAY, by="reviewer")
    assert project.change_state().review.reviewed
    project.replace(TASKS_FILE, "  - **Verify:** read the help text\n", ADDED)
    lifecycle.tick(project.root, NAME, "1.3", DAY)


def test_scenario_item_added_after_a_pass(project: Workspace) -> None:
    passed_then_added(project)
    state = project.change_state()
    assert state.review.uncovered == ("1.3",)
    assert state.review.to_review == ("1.3",)
    assert not state.review.reviewed
    assert state.next_step.kind is StepKind.REVIEW
    assert "Review item 1.3 only" in state.next_step.reason

    lifecycle.verdict(project.root, NAME, Verdict.PASS, "names fifty", LATER, by="reviewer")
    text = project.read(TASKS_FILE)
    assert text.endswith("- 2026-02-01 (review) pass covers 1.3 by reviewer: names fifty\n")
    assert "- 2026-01-15 (review) pass covers 1.1, 1.2 by reviewer: fine\n" in text
    state = project.change_state()
    assert state.review.reviewed
    assert state.review.uncovered == ()
    assert state.applied


def test_instructions_offer_a_review_of_the_added_items_only(project: Workspace) -> None:
    passed_then_added(project)
    payload = instructions(project.record(), None, NAME)
    assert payload["step"] == "review"
    assert any("Review only item 1.3" in line for line in payload["guidance"])


def test_a_self_review_of_added_items_covers_just_them(project: Workspace) -> None:
    passed_then_added(project, "self")
    lifecycle.self_review(project.root, NAME, "names fifty", LATER)
    assert project.read(TASKS_FILE).endswith(
        "- 2026-02-01 (self-review) covers 1.3 by planner for Sam Doe: names fifty\n"
    )
    assert project.change_state().review.reviewed


def test_a_changes_verdict_on_added_items_rebuilds_them_and_reviews_them_again(
    project: Workspace,
) -> None:
    passed_then_added(project)
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "says 51", LATER, items=["1.3"])
    assert (
        "- 2026-02-01 (review) changes 1.3; covers 1.3 by planner for Sam Doe: says 51\n"
        in project.read(TASKS_FILE)
    )
    lifecycle.reopen(project.root, NAME, "1.3", LATER)
    lifecycle.tick(project.root, NAME, "1.3", DAY)
    assert project.change_state().review.to_review == ("1.3",)


def test_scenario_archive_before_the_added_item_is_reviewed(project: Workspace) -> None:
    passed_then_added(project)
    before = project.read(TASKS_FILE)
    with pytest.raises(Refusal) as refusal:
        lifecycle.archive(project.root, NAME, LATER, built="Shipped.")
    assert "item 1.3 is not reviewed" in str(refusal.value)
    assert "--override" in str(refusal.value)
    assert project.read(TASKS_FILE) == before

    lifecycle.archive(project.root, NAME, LATER, built="Shipped.", override="reviewed in the PR")
    assert project.record().changes == {}


def test_scenario_older_review_records(project: Workspace) -> None:
    project.change(tasks=TASKS)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.2", DAY)
    project.write(
        TASKS_FILE,
        project.read(TASKS_FILE)
        + "- 2026-01-15 (self-review) by planner for Sam Doe: written before covers\n",
    )
    state = project.change_state()
    assert state.review.reviewed
    assert state.review.uncovered == ()
    assert project.record().problems == ()

    lifecycle.archive(project.root, NAME, LATER, built="Shipped.")
    assert project.record().problems == ()

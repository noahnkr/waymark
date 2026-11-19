"""Proposals, designs, the charter, milestones and explorations."""

from tests.support import CHARTER, DESIGN, GOAL_TEXT, NO_SPECS, document, milestone, proposal
from waymark.record.artifacts.charter import parse_charter
from waymark.record.artifacts.design import parse_design
from waymark.record.artifacts.explorations import Exploration, parse_exploration
from waymark.record.artifacts.milestones import append_milestone_log, parse_milestone
from waymark.record.artifacts.proposal import Proposal, parse_proposal
from waymark.record.terms import ReviewLevel
from waymark.record.writing import templates

EXPLORATION = """# Paging

- Status: {status}

## Context

Lists are long.

## Questions

- Is a cursor needed?

## Approaches

Offset or cursor.

## Conclusion

{conclusion}

## Related

Nothing yet.
"""


def parse(text: str) -> Proposal:
    return parse_proposal(document(text, "changes/add-limit/proposal.md"))


def proposal_codes(text: str) -> list[str]:
    return [problem.code for problem in parse(text).problems]


def explore(conclusion: str, status: str = "open") -> Exploration:
    text = EXPLORATION.format(conclusion=conclusion, status=status)
    return parse_exploration("paging", document(text, "explorations/paging.md"))


def test_proposal_has_an_owner_and_its_required_sections() -> None:
    parsed = parse(proposal())
    assert parsed.problems == ()
    assert parsed.owner == "Sam Doe"
    assert parsed.sections["Why"] == "Long result lists are slow."
    assert parsed.outcome is None
    assert not parsed.short_path


def test_proposal_without_an_owner_is_a_problem() -> None:
    assert proposal_codes(proposal().replace("Owner: Sam Doe\n", "")) == ["missing-owner"]
    assert proposal_codes(proposal(owner="")) == ["missing-owner"]


def test_proposal_missing_or_empty_section_is_a_problem() -> None:
    assert proposal_codes(proposal().replace("## Non-goals\n\nPaging.\n\n", "")) == [
        "missing-section"
    ]
    assert proposal_codes(proposal().replace("Paging.", "<!-- what is out of scope -->")) == [
        "empty-section"
    ]


def test_proposal_outcome_is_optional_until_archive() -> None:
    assert parse(proposal(outcome="Shipped as planned.")).outcome == "Shipped as planned."


def test_proposal_marks_the_short_path_with_a_path_line() -> None:
    assert parse(proposal(short=True)).short_path
    assert not parse(
        proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Path: full\n")
    ).short_path
    assert proposal_codes(
        proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Path: quick\n")
    ) == ["invalid-path"]


def test_proposal_impact_can_state_no_spec_changes() -> None:
    assert parse(proposal(impact=NO_SPECS)).no_spec_changes
    assert not parse(proposal()).no_spec_changes


def test_accepted_text_leaves_out_the_outcome() -> None:
    plain = parse(proposal())
    accepted = parse(proposal(outcome="Shipped."))
    assert accepted.accepted_text().rstrip("\n") == plain.accepted_text().rstrip("\n")
    assert "Owner: Sam Doe" in accepted.accepted_text()


def test_design_has_context_approach_decisions_and_risks() -> None:
    design = parse_design(document(DESIGN, "changes/add-limit/design.md"))
    assert design.problems == ()
    assert [decision.name for decision in design.decisions] == ["Where to cut"]
    assert design.sections["Approach"] == "Cut the result list after sorting."


def test_design_missing_section_is_a_problem() -> None:
    text = DESIGN.replace("## Risks and trade-offs\n\nSorting everything costs memory.\n", "")
    design = parse_design(document(text))
    assert [problem.code for problem in design.problems] == ["missing-section"]


def test_design_decision_gives_options_choice_and_why() -> None:
    design = parse_design(document(DESIGN.replace("- Why: the order must be final first\n", "")))
    assert [problem.code for problem in design.problems] == ["decision-incomplete"]
    unnamed = parse_design(
        document(DESIGN.replace("### Decision: Where to cut", "### Where to cut"))
    )
    assert [problem.code for problem in unnamed.problems] == ["decision-format"]


def test_charter_has_its_required_sections_and_context() -> None:
    charter = parse_charter(document(CHARTER, "charter.md"))
    assert charter.problems == ()
    assert charter.title == "Suite"
    assert charter.context == "The search index is rebuilt nightly."
    assert charter.sections["Vision"] == "Fast search for everyone."


def test_charter_rules_are_one_list() -> None:
    charter = parse_charter(document(CHARTER, "charter.md"))
    assert charter.rules == "1. Run the tests before reporting.\n2. Check every scenario."


def test_charter_missing_section_is_a_problem() -> None:
    text = CHARTER.replace(
        "## Glossary\n\n- **Match**: a document that satisfies the query.\n\n", ""
    )
    charter = parse_charter(document(text))
    assert [problem.code for problem in charter.problems] == ["missing-section"]


def test_charter_skeleton_with_empty_sections_is_readable() -> None:
    skeleton = "# Suite\n\n" + "".join(
        f"## {name}\n\n"
        for name in ("Vision", "Goals", "Non-goals", "Constraints", "Glossary", "Context", "Rules")
    )
    charter = parse_charter(document(skeleton))
    assert charter.problems == ()
    assert charter.context == ""
    assert charter.rules == ""


def test_milestone_has_goal_done_when_non_goals_and_roadmap() -> None:
    goal, roadmap = parse_milestone(document(milestone("- Cache hot queries\n")))
    assert goal.problems == ()
    assert goal.title == "Faster search"
    assert goal.sections["Done when"] == "- P95 is low."
    assert [entry.text for entry in roadmap.entries] == ["Cache hot queries"]
    missing, _ = parse_milestone(
        document(milestone().replace("## Done when\n\n- P95 is low.\n\n", ""))
    )
    assert [problem.code for problem in missing.problems] == ["missing-section"]


def test_milestone_sections_come_in_order() -> None:
    text = milestone("- Cache\n").replace("## Goal\n\nAnswers in a blink.\n\n", "")
    text = text.replace("## Roadmap", "## Goal\n\nAnswers in a blink.\n\n## Roadmap")
    goal, _ = parse_milestone(document(text))
    assert [problem.code for problem in goal.problems] == ["section-order"]


def test_roadmap_lists_links_to_changes_and_plain_lines() -> None:
    lines = (
        "- [x] [Limit results](../../changes/archive/2026-01-20-add-limit/proposal.md)\n"
        "- [ ] [Sort results](../../changes/add-order/)\n"
        "- [ ] Cache hot queries\n"
        "- A plain line\n"
    )
    _, roadmap = parse_milestone(
        document(milestone(lines), "milestones/faster-search/milestone.md")
    )
    assert roadmap.problems == ()
    assert [entry.target for entry in roadmap.entries] == [
        "../../changes/archive/2026-01-20-add-limit/proposal.md",
        "../../changes/add-order/",
        None,
        None,
    ]
    assert [entry.checked for entry in roadmap.entries] == [True, False, False, False]
    assert roadmap.entries[2].text == "Cache hot queries"


def test_only_roadmap_lines_are_entries() -> None:
    """Requirement "Milestone as one file": Done when bullets aren't roadmap entries."""
    _, roadmap = parse_milestone(document(milestone("- Cache hot queries\n")))
    assert [entry.text for entry in roadmap.entries] == ["Cache hot queries"]
    commented = milestone("<!-- An example:\n- not a change -->\n- Cache hot queries\n")
    _, roadmap = parse_milestone(document(commented))
    assert [entry.text for entry in roadmap.entries] == ["Cache hot queries"]


def test_exploration_with_an_empty_conclusion_is_open() -> None:
    exploration = explore("")
    assert exploration.problems == ()
    assert exploration.conclusion == ""
    assert exploration.sections["Questions"] == "- Is a cursor needed?"


def test_exploration_conclusion_links_are_collected() -> None:
    exploration = explore("Led to [add-paging](../changes/add-paging/proposal.md).")
    assert exploration.conclusion_links == ("../changes/add-paging/proposal.md",)


def test_exploration_missing_section_is_a_problem() -> None:
    text = EXPLORATION.format(conclusion="", status="open").replace(
        "## Related\n\nNothing yet.\n", ""
    )
    exploration = parse_exploration("paging", document(text))
    assert [problem.code for problem in exploration.problems] == ["missing-section"]


def test_proposal_review_line_sets_the_change_review_level() -> None:
    assert parse(proposal()).review is None
    reviewed = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: independent\n")
    assert parse(reviewed).review is ReviewLevel.INDEPENDENT
    assert proposal_codes(
        proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: strict\n")
    ) == ["invalid-review-level"]


LOGGED = (
    "\n## Log\n\n"
    "- 2026-11-20 (added) add-cache by Ada: cache hot queries\n"
    "- 2026-11-20 (moved) add-cache first by Ada\n"
    "- a line that isn't a record\n"
)


def test_milestone_log_is_read_as_records() -> None:
    goal, roadmap = parse_milestone(
        document(milestone("- add-cache: cache hot queries\n") + LOGGED)
    )
    assert [entry.text for entry in roadmap.entries] == ["add-cache: cache hot queries"]
    assert [(record.kind.value, record.change, record.after) for record in roadmap.log] == [
        ("added", "add-cache", None),
        ("moved", "add-cache", None),
    ]
    assert roadmap.log[0].text == "cache hot queries"
    assert goal.problems == ()


def test_scenario_log_not_last() -> None:
    text = "# Faster\n\n" + GOAL_TEXT + LOGGED + "\n## Roadmap\n\n- add-cache: cache hot queries\n"
    goal, roadmap = parse_milestone(document(text))
    assert "log-section-last" in [problem.code for problem in goal.problems]
    assert [entry.text for entry in roadmap.entries] == ["add-cache: cache hot queries"]


def test_records_are_appended_to_a_milestone_log() -> None:
    doc = document(milestone("- add-cache: cache hot queries\n\n"), "milestones/m/milestone.md")
    first = append_milestone_log(doc, "2026-11-20 (proposed) add-cache by Ada")
    assert first.endswith(
        "- add-cache: cache hot queries\n\n## Log\n\n- 2026-11-20 (proposed) add-cache by Ada\n"
    )
    second = append_milestone_log(
        document(first, "milestones/m/milestone.md"), "2026-11-21 (archived) add-cache by Ada"
    )
    assert second.endswith(
        "- 2026-11-20 (proposed) add-cache by Ada\n- 2026-11-21 (archived) add-cache by Ada\n"
    )


def test_a_milestone_log_keeps_the_file_line_endings() -> None:
    text = milestone("- add-cache: cache hot queries\n").replace("\n", "\r\n")
    appended = append_milestone_log(document(text), "2026-11-20 (proposed) add-cache")
    assert "\n" not in appended.replace("\r\n", "")
    assert appended.endswith("## Log\r\n\r\n- 2026-11-20 (proposed) add-cache\r\n")


def test_scenario_new_milestone_has_no_log() -> None:
    _, roadmap = parse_milestone(document(templates.render(templates.MILESTONE, title="Fast")))
    assert roadmap.log == ()
    assert "## Log" not in templates.render(templates.MILESTONE, title="Fast")

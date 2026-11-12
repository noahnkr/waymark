"""Proposals, designs, the charter, milestones and explorations."""

import datetime

from tests.support import CHARTER, DESIGN, document, proposal
from waymark.record.charter import parse_charter
from waymark.record.design import parse_design
from waymark.record.explorations import Exploration, parse_exploration
from waymark.record.milestones import parse_goal, parse_roadmap
from waymark.record.proposal import Proposal, format_acceptance, parse_proposal
from waymark.record.terms import Step

ACCEPTED = "Accepted: 2026-01-15 by Sam Doe (fingerprint: 0123456789abcdef)"

EXPLORATION = """# Paging

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


def explore(conclusion: str) -> Exploration:
    text = EXPLORATION.format(conclusion=conclusion)
    return parse_exploration("paging", document(text, "explorations/paging.md"))


def test_proposal_has_an_owner_and_its_required_sections() -> None:
    parsed = parse(proposal())
    assert parsed.problems == ()
    assert parsed.owner == "Sam Doe"
    assert parsed.sections["Why"] == "Long result lists are slow."
    assert parsed.acceptance is None
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


def test_proposal_acceptance_line_holds_date_person_and_fingerprint() -> None:
    parsed = parse(proposal().replace("Owner: Sam Doe\n", f"Owner: Sam Doe\n{ACCEPTED}\n"))
    assert parsed.problems == ()
    assert parsed.acceptance is not None
    assert parsed.acceptance.date == datetime.date(2026, 1, 15)
    assert parsed.acceptance.who == "Sam Doe"
    assert parsed.acceptance.fingerprint == "0123456789abcdef"
    assert format_acceptance(datetime.date(2026, 1, 15), "Sam Doe", "0123456789abcdef") == ACCEPTED


def test_proposal_acceptance_line_that_breaks_the_format_is_malformed_evidence() -> None:
    broken = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\nAccepted: yes, looks good\n")
    parsed = parse(broken)
    assert [problem.code for problem in parsed.problems] == ["malformed-evidence"]
    assert parsed.acceptance is None


def test_proposal_marks_the_short_path_with_a_path_line() -> None:
    assert parse(proposal(short=True)).short_path
    assert not parse(
        proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\nPath: full\n")
    ).short_path
    assert proposal_codes(
        proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\nPath: quick\n")
    ) == ["invalid-path"]


def test_proposal_impact_can_state_no_spec_changes() -> None:
    assert parse(proposal(impact="No spec changes.")).no_spec_changes
    assert not parse(proposal()).no_spec_changes


def test_accepted_text_leaves_out_the_acceptance_line_and_the_outcome() -> None:
    plain = parse(proposal())
    accepted = parse(
        proposal(outcome="Shipped.").replace("Owner: Sam Doe\n", f"Owner: Sam Doe\n{ACCEPTED}\n")
    )
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


def test_charter_rules_are_kept_per_workflow_step() -> None:
    charter = parse_charter(document(CHARTER, "charter.md"))
    assert charter.rules == {
        Step.APPLY: "Run the tests before reporting.",
        Step.REVIEW: "Check every scenario.",
    }
    assert Step.DESIGN not in charter.rules


def test_charter_rules_for_an_unknown_step_are_a_problem() -> None:
    charter = parse_charter(document(CHARTER.replace("### apply", "### deploy")))
    assert [problem.code for problem in charter.problems] == ["unknown-step"]


def test_charter_missing_section_is_a_problem() -> None:
    text = CHARTER.replace("## Glossary\n\n- Match: a document that satisfies the query.\n\n", "")
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
    assert charter.rules == {}


def test_goal_has_goal_done_when_and_non_goals() -> None:
    text = (
        "# Faster search\n\n## Goal\n\nAnswers in a blink.\n\n"
        "## Done when\n\nP95 is low.\n\n## Non-goals\n\nRanking.\n"
    )
    goal = parse_goal(document(text))
    assert goal.problems == ()
    assert goal.sections["Done when"] == "P95 is low."
    missing = parse_goal(document(text.replace("## Done when\n\nP95 is low.\n\n", "")))
    assert [problem.code for problem in missing.problems] == ["missing-section"]


def test_roadmap_lists_links_to_changes_and_plain_lines() -> None:
    text = (
        "# Roadmap\n\n"
        "- [x] [Limit results](../../changes/archive/2026-01-20-add-limit/proposal.md)\n"
        "- [ ] [Sort results](../../changes/add-order/)\n"
        "- [ ] Cache hot queries\n"
        "- A plain line\n"
    )
    roadmap = parse_roadmap(document(text, "milestones/faster-search/roadmap.md"))
    assert roadmap.problems == ()
    assert [entry.target for entry in roadmap.entries] == [
        "../../changes/archive/2026-01-20-add-limit/proposal.md",
        "../../changes/add-order/",
        None,
        None,
    ]
    assert [entry.checked for entry in roadmap.entries] == [True, False, False, False]
    assert roadmap.entries[2].text == "Cache hot queries"


def test_exploration_with_an_empty_conclusion_is_open() -> None:
    exploration = explore("")
    assert exploration.problems == ()
    assert exploration.conclusion == ""
    assert exploration.parked is None
    assert exploration.sections["Questions"] == "- Is a cursor needed?"


def test_exploration_parked_conclusion_gives_a_reason() -> None:
    assert explore("Parked: not needed this year").parked == "not needed this year"
    assert [problem.code for problem in explore("Parked:").problems] == ["parked-without-reason"]


def test_exploration_conclusion_links_are_collected() -> None:
    exploration = explore("Led to [add-paging](../changes/add-paging/proposal.md).")
    assert exploration.conclusion_links == ("../changes/add-paging/proposal.md",)


def test_exploration_missing_section_is_a_problem() -> None:
    text = EXPLORATION.format(conclusion="").replace("## Related\n\nNothing yet.\n", "")
    exploration = parse_exploration("paging", document(text))
    assert [problem.code for problem in exploration.problems] == ["missing-section"]

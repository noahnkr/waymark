"""The layouts humans and the planner write: facts, the glossary, the exploration status."""

import datetime
import re

from tests.record.artifacts.test_resources import resource
from tests.support import (
    CHARTER,
    DESIGN,
    NO_SPECS,
    Workspace,
    delta,
    document,
    proposal,
    spec,
)
from waymark.record.artifacts.charter import parse_charter
from waymark.record.artifacts.deltas import parse_delta
from waymark.record.artifacts.design import parse_design
from waymark.record.artifacts.explorations import parse_exploration
from waymark.record.artifacts.proposal import parse_proposal
from waymark.record.artifacts.resources import parse_resource
from waymark.record.artifacts.specs import parse_spec
from waymark.record.artifacts.tasks import parse_tasks
from waymark.record.state import AcceptanceState, ExplorationStatus, derive_state
from waymark.services import setup
from waymark.services.context import context_pack
from waymark.services.instructions import instructions

EXPLORATION = (
    "# Paging\n\n{status}"
    "## Context\n\nLists are long.\n\n## Questions\n\n- Cursor?\n\n## Approaches\n\nOffset.\n\n"
    "## Conclusion\n\n{conclusion}\n\n## Related\n\nNothing yet.\n"
)


def explore(status: str, conclusion: str = "") -> str:
    return EXPLORATION.format(
        status=f"- Status: {status}\n\n" if status else "", conclusion=conclusion
    )


def codes(text: str) -> list[str]:
    return [
        p.code
        for p in parse_exploration("paging", document(text, "explorations/paging.md")).problems
    ]


def test_proposal_facts_as_a_list() -> None:
    """Requirement "Proposal facts as a list": bulleted facts are read."""
    text = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: independent\n")
    parsed = parse_proposal(document(text, "changes/add-limit/proposal.md"))
    assert parsed.problems == ()
    assert parsed.owner == "Sam Doe"
    assert parsed.review is not None
    assert parsed.review.value == "independent"


def test_structured_impact() -> None:
    """Requirement "Structured impact": the three lines are read, with nested bullets."""
    impact = (
        "- Specs: `search` (modified), `ranking` (new)\n"
        "- User-visible:\n  - at most fifty results\n  - a new flag\n"
        "- Code: `record/search.py`\n"
        "- Assets: the skills\n"
    )
    parsed = parse_proposal(document(proposal(impact=impact), "changes/add-limit/proposal.md"))
    assert parsed.problems == ()
    assert parsed.impact_specs == ("search", "ranking")
    assert parsed.impact["User-visible"] == "- at most fifty results\n- a new flag"
    assert not parsed.no_spec_changes
    none = parse_proposal(document(proposal(impact=NO_SPECS), "p.md"))
    assert none.impact_specs == ()
    assert none.no_spec_changes
    for value in ("", " search (new)"):
        text = proposal(impact=NO_SPECS.replace("- Specs: none", f"- Specs:{value}"))
        unnamed = parse_proposal(document(text, "p.md"))
        assert (unnamed.impact_specs, unnamed.no_spec_changes) == (None, False)


def test_scenario_new_change(project: Workspace) -> None:
    setup.create_change(project.root, "add-limit", short=True)
    text = project.read("changes/add-limit/proposal.md")
    assert "\n- **Owner:** Sam Doe\n- **Path:** short\n" in text
    change = project.record().changes["add-limit"]
    assert change.short_path
    assert change.proposal is not None
    assert change.proposal.owner == "Sam Doe"
    assert {p.code for p in change.problems} == {"empty-section"}


def test_glossary_as_a_list() -> None:
    """Requirement "Glossary as a list": entries pass, other lines are reported."""
    assert parse_charter(document(CHARTER, "charter.md")).problems == ()
    prose = CHARTER.replace(
        "- **Match**: a document that satisfies the query.\n",
        "- **Match**: a document that satisfies the query.\nSome loose prose about terms.\n",
    )
    assert [p.code for p in parse_charter(document(prose, "charter.md")).problems] == [
        "glossary-format"
    ]


def charter_problems(text: str) -> list[tuple[int, str]]:
    return [(p.line, p.code) for p in parse_charter(document(text, "charter.md")).problems]


def test_scenario_bulleted_goal() -> None:
    bulleted = CHARTER.replace("1. Answers in one step.", "- Answers in one step.")
    [problem] = parse_charter(document(bulleted, "charter.md")).problems
    assert problem.code == "numbered-list-format"
    assert "1. <text>" in problem.message


def test_scenario_step_heading_under_rules() -> None:
    """Requirement "Numbered goals, constraints and rules": a heading is reported."""
    heading = CHARTER.replace(
        "1. Run the tests before reporting.\n2. Check every scenario.\n",
        "### Apply\n\n1. Run the full checks.\n",
    )
    doc = document(heading, "charter.md")
    [problem] = parse_charter(doc).problems
    assert problem.code == "numbered-list-format"
    assert "1. <text>" in problem.message
    assert doc.lines[problem.line - 1].text == "### Apply"


def test_scenario_no_rules() -> None:
    commented = CHARTER.replace(
        "1. Run the tests before reporting.\n2. Check every scenario.\n",
        "<!-- The project's own rules. -->\n",
    )
    charter = parse_charter(document(commented, "charter.md"))
    assert charter.problems == ()


def test_bulleted_rule_is_reported() -> None:
    bulleted = CHARTER.replace(
        "1. Run the tests before reporting.\n2. Check every scenario.\n",
        "- Run the tests before reporting.\n",
    )
    [problem] = parse_charter(document(bulleted, "charter.md")).problems
    assert problem.code == "numbered-list-format"
    assert problem.message.startswith("Rules are a numbered list")


def test_numbered_goals_and_constraints() -> None:
    """Requirement "Numbered goals and constraints": counted from 1, indented lines continue."""
    two = CHARTER.replace(
        "1. Answers in one step.\n",
        "1. Answers in one step.\n   Even for long queries.\n2. Works offline.\n",
    )
    assert charter_problems(two) == []
    skipped = CHARTER.replace("1. Answers in one step.\n", "1. One.\n3. Three.\n4. Four.\n")
    assert [code for _, code in charter_problems(skipped)] == ["numbered-list-format"]
    commented = CHARTER.replace("1. Runs offline.\n", "<!-- - a note -->\n1. Runs offline.\n")
    assert charter_problems(commented) == []


def test_scenario_item_without_verification(workspace: Workspace) -> None:
    tasks = BUILT.replace("  - Verify: the index answers\n", "")
    workspace.change(tasks=tasks)
    [problem] = workspace.record().changes["add-limit"].problems
    assert (problem.code, problem.line) == (
        "item-incomplete",
        tasks.split("\n").index("- [ ] 1.2 Rebuild the index") + 1,
    )
    assert '"- **Verify:**"' in problem.message
    assert '"- **Criteria:**"' not in problem.message


LISTED_OPTIONS = "- Options:\n  - in the query\n  - after sorting\n"


def test_scenario_one_option(workspace: Workspace) -> None:
    workspace.change(
        design=bold(DESIGN.replace(LISTED_OPTIONS, "- Options:\n  - cut after sorting\n"))
    )
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "decision-options"
    assert "at least two options" in problem.message
    assert "one option per bullet" in problem.message


def test_scenario_options_as_a_list(workspace: Workspace) -> None:
    workspace.change(design=bold(DESIGN))
    assert workspace.record().changes["add-limit"].problems == ()
    design = parse_design(document(bold(DESIGN), "changes/add-limit/design.md"))
    assert design.decisions[0].options == ("in the query", "after sorting")


def test_scenario_options_on_one_line(workspace: Workspace) -> None:
    """The old one-line form is not split on "or": it is reported, on its own line."""
    design = bold(DESIGN.replace(LISTED_OPTIONS, "- Options: cut before or after sorting\n"))
    workspace.change(design=design)
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "decision-options"
    assert (
        problem.line == design.split("\n").index("- **Options:** cut before or after sorting") + 1
    )
    assert "one option per bullet" in problem.message
    parsed = parse_design(document(design, "changes/add-limit/design.md"))
    assert parsed.decisions[0].options == ()


def test_archived_changes_are_not_held_to_items_and_options(workspace: Workspace) -> None:
    folder = "changes/archive/2026-01-20-add-limit"
    workspace.write(f"{folder}/proposal.md", proposal(outcome="- Built: x\n- Differs: none"))
    workspace.write(f"{folder}/design.md", DESIGN.replace(LISTED_OPTIONS, "- Options: one\n"))
    workspace.write(f"{folder}/tasks.md", "# Tasks\n\n## 1. Limit\n\n- [x] 1.1 Cap it\n")
    assert workspace.record().problems == ()


def test_settled_decisions_are_checked(workspace: Workspace) -> None:
    """Requirement "Settled decisions": the two lines and the section are required."""
    workspace.change(design=DESIGN.replace("- Decided by: planner\n", "- Decided by: Sam\n"))
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "decision-format"
    assert '"- **Decided by:** human" or "- **Decided by:** planner"' in problem.message
    workspace.change(design=DESIGN.replace("- Status: decided\n", ""))
    [problem] = workspace.record().changes["add-limit"].problems
    assert (problem.code, "the line is missing" in problem.message) == ("decision-format", True)
    workspace.change(design=DESIGN.replace("## Open questions\n\nNone.\n\n", ""))
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "missing-section"
    workspace.change(design=DESIGN.replace("None.", "We may cut later."))
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "open-questions-format"


def test_open_questions_are_read() -> None:
    text = DESIGN.replace("None.", "- Fifty or twenty?\n- Who decides?")
    design = parse_design(document(text, "changes/add-limit/design.md"))
    assert design.open_questions == ("Fifty or twenty?", "Who decides?")
    assert design.decisions[0].status == "decided"
    assert design.decisions[0].decided_by == "planner"


def test_exploration_status() -> None:
    """Requirement "Exploration status": the line is read and checked."""
    assert codes(explore("open")) == []
    assert codes(explore("dropped")) == []
    assert codes(explore("someday")) == ["unknown-status"]
    assert codes(explore("led-to")) == ["unknown-status"]


def test_scenario_new_exploration(workspace: Workspace) -> None:
    setup.create_exploration(workspace.root, "result-paging")
    text = workspace.read("explorations/result-paging.md")
    assert "\n- **Status:** open\n" in text
    built = context_pack(workspace.record(), "explore")
    assert built["explorations"][0]["status"] == "open"


def test_scenario_parked_is_not_a_status() -> None:
    [problem] = parse_exploration("paging", document(explore("parked"), "e.md")).problems
    assert problem.code == "unknown-status"
    for status in ("open", "led-to", "dropped"):
        assert f"- **Status:** {status}" in problem.message


def test_scenario_missing_status() -> None:
    [problem] = parse_exploration("paging", document(explore(""), "e.md")).problems
    assert problem.code == "missing-status"
    for status in ("open", "led-to", "dropped"):
        assert f"- **Status:** {status}" in problem.message
    assert "wm update" not in problem.message


def test_dropped_exploration_gives_its_reason(workspace: Workspace) -> None:
    workspace.write("explorations/paging.md", explore("dropped", "Results never pass fifty."))
    state = derive_state(workspace.record()).explorations["paging"]
    assert (state.status, state.detail) == (ExplorationStatus.DROPPED, "Results never pass fifty.")


def test_led_to_status_points_at_its_change(workspace: Workspace) -> None:
    workspace.change()
    workspace.write(
        "explorations/paging.md", explore("led-to [add-limit](../changes/add-limit/proposal.md)")
    )
    state = derive_state(workspace.record()).explorations["paging"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, "change add-limit")


BUILT = (
    "# Tasks\n\n## 1. Limit\n\n"
    "- [ ] 1.1 Cap it\n"
    "  - Criteria:\n"
    "    - fifty at most\n"
    "    - sorted by score\n"
    "  - Verify: a test\n"
    "- [ ] 1.2 Rebuild the index\n"
    "  - Criteria: rebuilt\n"
    "  - Verify: the index answers\n"
    "  - Build: delegate\n"
)


def test_scenario_nested_criteria(workspace: Workspace) -> None:
    workspace.change(tasks=BUILT)
    workspace.accept()
    item = context_pack(workspace.record(), "implement", "add-limit", "1.1")["item"]
    assert item["criteria"] == "- fifty at most\n- sorted by score"


def test_scenario_nested_verification(workspace: Workspace) -> None:
    built = BUILT.replace(
        "  - Verify: a test\n", "  - Verify:\n    - a test for the limit\n    - wm check here\n"
    )
    workspace.change(tasks=built)
    workspace.accept()
    item = context_pack(workspace.record(), "implement", "add-limit", "1.1")["item"]
    assert item["verify"] == "- a test for the limit\n- wm check here"


def test_scenario_tagged_item(workspace: Workspace) -> None:
    workspace.change(tasks=BUILT)
    workspace.accept()
    workspace.replace("changes/add-limit/tasks.md", "- [ ] 1.1", "- [x] 1.1")
    guide = instructions(workspace.record(), "apply", "add-limit")
    assert guide["item"] == "1.2"
    assert any("implementer" in line for line in guide["guidance"])


def test_scenario_unknown_build_value() -> None:
    tasks = parse_tasks(document(BUILT.replace("Build: delegate", "Build: someone"), "t.md"))
    [problem] = tasks.problems
    assert problem.code == "unknown-build-tag"
    assert "delegate" in problem.message
    assert not tasks.items[1].delegate


def test_scenario_tag_added_after_acceptance(workspace: Workspace) -> None:
    workspace.change(tasks=BUILT.replace("  - Build: delegate\n", ""))
    workspace.accept()
    assert workspace.change_state().acceptance is AcceptanceState.VALID
    workspace.replace(
        "changes/add-limit/tasks.md",
        "  - Criteria: rebuilt\n",
        "  - Criteria: rebuilt\n  - Build: delegate\n",
    )
    assert workspace.change_state().acceptance is AcceptanceState.WITHDRAWN


def test_proposal_facts_include_the_milestone_line() -> None:
    """Requirement "Proposal facts as a list": `- Milestone:` is one of the facts."""
    text = proposal().replace(
        "- Owner: Sam Doe\n", "- Owner: Sam Doe\n- Milestone: faster-search\n"
    )
    parsed = parse_proposal(document(text, "changes/add-limit/proposal.md"))
    assert (parsed.milestone, parsed.milestone_line) == ("faster-search", 4)
    assert parsed.problems == ()
    bare = text.replace("- Milestone: faster-search", "Milestone: faster-search")
    assert parse_proposal(document(bare, "changes/add-limit/proposal.md")).milestone is None
    assert parse_proposal(document(proposal(), "changes/add-limit/proposal.md")).milestone is None


def test_proposal_facts_include_the_after_line() -> None:
    """Requirement "Proposal facts as a list": `- After:` is one of the facts."""
    text = proposal().replace("- Owner: Sam Doe\n", "- Owner: Sam Doe\n- After: add-index\n")
    parsed = parse_proposal(document(text, "changes/add-limit/proposal.md"))
    assert (parsed.after, parsed.after_line) == ("add-index", 4)
    assert parsed.problems == ()
    bare = text.replace("- After: add-index", "After: add-index")
    assert parse_proposal(document(bare, "changes/add-limit/proposal.md")).after is None


_PLAIN_LABEL = re.compile(
    r"^(\s*(?:[-*] )?)(Owner|Milestone|After|Path|Review|Specs|User-visible|Code|Built|Differs"
    r"|Build|Repo|Criteria|Verify|Status|Decided by|Options|Choice|Why|From|To|Reason|Repos"
    r"|Kind|Serves|Verified):",
    re.MULTILINE,
)


def bold(text: str) -> str:
    """The text with every known label written bold, the colon inside."""
    return _PLAIN_LABEL.sub(r"\1**\2:**", text)


def test_bold_labels_in_a_proposal() -> None:
    """Facts, Impact and Outcome are read with bold labels."""
    text = bold(
        proposal(outcome="- Built: the cap\n- Differs: none").replace(
            "- Owner: Sam Doe\n",
            "- Owner: Sam Doe\n- Milestone: faster-search\n- After: add-index\n"
            "- Path: short\n- Review: self\n",
        )
    )
    assert "- **Owner:** Sam Doe" in text
    parsed = parse_proposal(document(text, "changes/add-limit/proposal.md"))
    assert parsed.problems == ()
    assert (parsed.owner, parsed.milestone, parsed.after) == (
        "Sam Doe",
        "faster-search",
        "add-index",
    )
    assert parsed.short_path
    assert parsed.review is not None
    assert parsed.review.value == "self"
    assert parsed.impact_specs == ("search",)
    assert parsed.impact["User-visible"] == "at most fifty results"
    assert parsed.outcome_lines == {"Built": "the cap", "Differs": "none"}


def test_bold_labels_in_a_task_list() -> None:
    """An item's Criteria, Verify, Repo and Build are read with bold labels."""
    text = bold(BUILT.replace("  - Verify: a test\n", "  - Verify: a test\n  - Repo: api\n"))
    assert "  - **Criteria:**\n" in text
    tasks = parse_tasks(document(text, "changes/add-limit/tasks.md"))
    assert tasks.problems == ()
    first, second = tasks.items
    assert (first.criteria, first.verify, first.repo) == (
        "- fifty at most\n- sorted by score",
        "a test",
        "api",
    )
    assert second.delegate


def test_bold_labels_in_a_design() -> None:
    """A decision's parts are read with bold labels."""
    text = bold(DESIGN)
    assert "- **Decided by:** planner" in text
    design = parse_design(document(text, "changes/add-limit/design.md"))
    assert design.problems == ()
    [decision] = design.decisions
    assert (decision.status, decision.decided_by) == ("decided", "planner")
    assert decision.options == ("in the query", "after sorting")


def test_bold_labels_in_a_delta() -> None:
    """A delta's Repos, From, To and Reason are read with bold labels."""
    text = bold(delta(removed=(("Result order", "Unused."),), repos="api, web"))
    assert "**Reason:** Unused." in text
    parsed = parse_delta("search", document(text, "changes/add-limit/specs/search.md"))
    assert parsed.problems == ()
    assert parsed.repos == ("api", "web")
    assert [(r.name, r.reason) for r in parsed.removed] == [("Result order", "Unused.")]
    renamed = bold(
        "# Search\n\n## RENAMED Requirements\n\n- From: Result cap\n- To: Result limit\n"
    )
    parsed = parse_delta("search", document(renamed, "changes/add-limit/specs/search.md"))
    assert parsed.problems == ()
    assert [(r.old, r.new) for r in parsed.renamed] == [("Result cap", "Result limit")]


def test_bold_repos_line_in_a_spec() -> None:
    text = spec().replace("# Search\n\n", "# Search\n\n**Repos:** api\n\n")
    parsed = parse_spec("search", document(text, "specs/search.md"))
    assert parsed.problems == ()
    assert parsed.repos == ("api",)


def test_bold_status_in_an_exploration() -> None:
    text = bold(explore("led-to [add-limit](../changes/add-limit/proposal.md)"))
    assert "- **Status:** led-to" in text
    parsed = parse_exploration("paging", document(text, "explorations/paging.md"))
    assert parsed.problems == ()
    assert parsed.status == "led-to"


def test_bold_lines_in_a_resource() -> None:
    text = bold(resource())
    assert "- **Verified:** 2026-11-17" in text
    parsed = parse_resource("stripe", document(text, "resources/stripe.md"))
    assert parsed.problems == ()
    assert (parsed.kind, parsed.status, parsed.verified) == (
        "service",
        "active",
        datetime.date(2026, 11, 17),
    )


def test_glossary_with_the_colon_inside_the_bold() -> None:
    text = CHARTER.replace("- **Match**: a document", "- **Match:** a document")
    assert parse_charter(document(text, "charter.md")).problems == ()
    assert parse_charter(document(CHARTER, "charter.md")).problems == ()


def test_bold_labels_report_nothing_new(workspace: Workspace) -> None:
    """A change written with bold labels throughout checks clean and can be accepted."""
    workspace.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(BUILT))
    assert workspace.record().changes["add-limit"].problems == ()
    workspace.accept()
    assert workspace.change_state().acceptance is AcceptanceState.VALID

"""The layouts humans and the planner write: facts, the glossary, the exploration status."""

from tests.support import CHARTER, DESIGN, NO_SPECS, Workspace, document, proposal
from waymark.record.charter import parse_charter
from waymark.record.design import parse_design
from waymark.record.explorations import parse_exploration
from waymark.record.proposal import parse_proposal
from waymark.record.state import AcceptanceState, ExplorationStatus, derive_state
from waymark.record.tasks import parse_tasks
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


def test_scenario_new_change(project: Workspace) -> None:
    setup.create_change(project.root, "add-limit", short=True)
    text = project.read("changes/add-limit/proposal.md")
    assert "\n- Owner: Sam Doe\n- Path: short\n" in text
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
    capitalized = CHARTER.replace("### apply", "### Apply")
    assert parse_charter(document(capitalized, "charter.md")).problems == ()


def charter_problems(text: str) -> list[tuple[int, str]]:
    return [(p.line, p.code) for p in parse_charter(document(text, "charter.md")).problems]


def test_scenario_bulleted_goal() -> None:
    bulleted = CHARTER.replace("1. Answers in one step.", "- Answers in one step.")
    [problem] = parse_charter(document(bulleted, "charter.md")).problems
    assert problem.code == "numbered-list-format"
    assert "1. <text>" in problem.message


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


def test_settled_decisions_are_checked(workspace: Workspace) -> None:
    """Requirement "Settled decisions": the two lines and the section are required."""
    workspace.change(design=DESIGN.replace("- Decided by: planner\n", "- Decided by: Sam\n"))
    [problem] = workspace.record().changes["add-limit"].problems
    assert problem.code == "decision-format"
    assert '"- Decided by: human" or "- Decided by: planner"' in problem.message
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
    assert codes(explore("someday")) == ["unknown-status"]
    assert codes(explore("led-to")) == ["unknown-status"]


def test_scenario_parked_exploration(workspace: Workspace) -> None:
    workspace.write("explorations/paging.md", explore("parked", "Waits for a second user."))
    record = workspace.record()
    state = derive_state(record).explorations["paging"]
    assert (state.status, state.detail) == (ExplorationStatus.PARKED, "Waits for a second user.")
    built = context_pack(record, "explore")
    assert built["explorations"][0]["status"] == "parked"


def test_scenario_missing_status() -> None:
    [problem] = parse_exploration("paging", document(explore(""), "e.md")).problems
    assert problem.code == "missing-status"
    assert '"- Status: open"' in problem.message
    assert "wm update" not in problem.message


def test_scenario_parked_in_the_conclusion_only(workspace: Workspace) -> None:
    workspace.write("explorations/paging.md", explore("open", "Parked: waits for a second user."))
    state = derive_state(workspace.record()).explorations["paging"]
    assert state.status is ExplorationStatus.OPEN
    built = context_pack(workspace.record(), "explore")
    assert built["explorations"][0]["status"] == "open"
    assert codes(explore("open", "Parked:")) == []


def test_parked_reason_is_the_conclusion() -> None:
    parsed = parse_exploration("paging", document(explore("parked", "Waits."), "e.md"))
    assert parsed.parked == "Waits."


def test_scenario_parked_without_a_reason() -> None:
    assert codes(explore("parked")) == ["parked-without-reason"]


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
    "  - Build: delegate\n"
)


def test_scenario_nested_criteria(workspace: Workspace) -> None:
    workspace.change(tasks=BUILT)
    workspace.accept()
    item = context_pack(workspace.record(), "implement", "add-limit", "1.1")["item"]
    assert item["criteria"] == "- fifty at most\n- sorted by score"


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

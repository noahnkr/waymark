"""The layouts humans and the planner write: facts, the glossary, the exploration status."""

from tests.support import CHARTER, Workspace, document, proposal
from waymark.record.charter import parse_charter
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

"""The agent interface: instructions for each step, and context packs for each job."""

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

import waymark
from tests.support import (
    ATLAS_CONFIG,
    CHARTER,
    DESIGN,
    TASKS,
    Workspace,
    delta,
    milestone,
    proposal,
    requirement,
    spec,
)
from tests.views.validator import errors
from waymark.record.deltas import parse_delta
from waymark.record.design import parse_design
from waymark.record.state import StepKind
from waymark.record.tasks import parse_tasks
from waymark.record.terms import Verdict
from waymark.record.text import Document
from waymark.services import lifecycle
from waymark.services.common import Refusal
from waymark.services.context import RESULT_LINE, VERDICT_LINE, context_pack, delegation_problems
from waymark.services.guidance import SEVERITY_RUBRIC, STOPPING_RULES
from waymark.services.instructions import (
    CHECKLISTS,
    FACT_RULE,
    SHARED_RULES,
    SIZING_RULES,
    WRITING_RULES,
    instructions,
)
from waymark.views import render
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

NAME = "add-limit"
FOLDER = f"changes/{NAME}"
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
PLAIN = Style()
FINDING = '--finding "<critical|warning|suggestion>: <place>: <text>"'
RULES = CHARTER + "3. Keep items small.\n4. Ask before assuming.\n"
CHARTER_RULES = "1. Run the tests before reporting.\n2. Check every scenario."
ALL_RULES = CHARTER_RULES + "\n3. Keep items small.\n4. Ask before assuming."


def valid(payload: dict[str, Any]) -> dict[str, Any]:
    name = payload["schema"].removeprefix("wm.")
    assert errors(render.public(payload), SCHEMAS[name]) == []
    assert json.loads(render.to_json(payload)) == render.public(payload)
    assert render.to_text(payload, PLAIN)
    return payload


def at(project: Workspace, step: str | None = None) -> dict[str, Any]:
    return valid(instructions(project.record(), step, NAME))


def pack(project: Workspace, role: str, number: str | None = "1.1") -> dict[str, Any]:
    if role == "review":
        number = None
    return valid(context_pack(project.record(), role, NAME, number))


def refused(project: Workspace, role: str, number: str | None = "1.1") -> str:
    if role == "review":
        number = None
    with pytest.raises(Refusal) as refusal:
        context_pack(project.record(), role, NAME, number)
    return str(refusal.value)


def accepted(project: Workspace, tasks: str = TASKS, **options: Any) -> Workspace:
    project.change(tasks=tasks, **options)
    lifecycle.accept(project.root, NAME, DAY)
    return project


INDEPENDENT = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: independent\n")


def test_instructions_give_the_right_next_step_at_every_stop(project: Workspace) -> None:
    project.write(f"{FOLDER}/proposal.md", "# Limit\n\nOwner: Sam Doe\n")
    step = at(project)
    assert (step["step"], step["ready"]) == ("propose", True)
    assert step["outputs"] == [
        {"path": f"waymark/{FOLDER}/proposal.md", "exists": True, "template": None}
    ]

    project.write(f"{FOLDER}/proposal.md", proposal())
    step = at(project)
    assert step["step"] == "specs"
    assert step["outputs"][0]["path"] == f"waymark/{FOLDER}/specs/<domain>.md"
    assert not step["outputs"][0]["exists"]
    assert f"waymark/{FOLDER}/proposal.md" in step["read"]

    project.write(
        f"{FOLDER}/specs/search.md", delta(added=(requirement(),), purpose="How search behaves.")
    )
    step = at(project)
    assert step["step"] == "design"
    assert step["outputs"][0]["path"] == f"waymark/{FOLDER}/design.md"
    assert f"waymark/{FOLDER}/specs/search.md" in step["read"]

    project.write(f"{FOLDER}/design.md", DESIGN)
    step = at(project)
    assert step["step"] == "tasks"
    assert step["outputs"][0]["path"] == f"waymark/{FOLDER}/tasks.md"
    assert f"waymark/{FOLDER}/design.md" in step["read"]

    project.write(f"{FOLDER}/tasks.md", TASKS)
    step = at(project)
    assert step["step"] == "accept"
    assert step["commands"] == [f"wm accept {NAME}"]

    lifecycle.accept(project.root, NAME, DAY)
    step = at(project)
    assert (step["step"], step["item"]) == ("apply", "1.1")
    assert step["commands"][0] == f"wm context {NAME} 1.1 --for implement"

    lifecycle.tick(project.root, NAME, "1.1")
    assert (at(project)["step"], at(project)["item"]) == ("apply", "1.2")

    lifecycle.tick(project.root, NAME, "1.2")
    step = at(project)
    assert (step["step"], step["item"]) == ("review", None)
    assert step["commands"] == [
        f'wm review {NAME} --self "<summary>" [{FINDING}]',
        f'wm verdict {NAME} changes "<reasons>" --items <item>...',
    ]

    lifecycle.self_review(project.root, NAME, "fine", DAY)
    step = at(project)
    assert step["step"] == "archive"
    assert step["commands"] == [
        f'wm archive {NAME} --built "<what was built>" --differs "<how it differs>"'
    ]


def test_instructions_skip_the_design_on_the_short_path(project: Workspace) -> None:
    project.change(proposal_text=proposal(short=True), design=None, tasks=None)
    assert at(project)["step"] == "tasks"
    design = at(project, "design")
    assert not design["ready"]
    assert "short path" in design["reason"]
    assert any("short path" in line for line in at(project, "propose")["guidance"])


def test_instructions_for_a_later_step_say_what_comes_first(project: Workspace) -> None:
    project.change(design=None, tasks=None)
    later = at(project, "tasks")
    assert not later["ready"]
    assert 'at "design", which comes first' in later["reason"]
    assert at(project, "specs")["ready"]


def test_instructions_warn_that_editing_an_accepted_change_withdraws_acceptance(
    project: Workspace,
) -> None:
    accepted(project)
    earlier = at(project, "specs")
    assert earlier["ready"]
    assert "withdraws its acceptance" in earlier["reason"]


def test_scenario_specs_checklist(project: Workspace) -> None:
    project.change(deltas={}, design=None, tasks=None)
    checklist = valid(at(project))["checklist"]
    assert at(project)["step"] == "specs"
    assert {"text": "Every requirement says SHALL.", "enforced": True} in checklist
    assert {
        "text": "Each THEN can be checked by someone who didn't write it.",
        "enforced": False,
    } in checklist


def test_scenario_specs_step(project: Workspace) -> None:
    """Requirement "Writing and sizing rules": the specs step gives the writing rules."""
    project.change(deltas={}, design=None, tasks=None)
    guidance = valid(at(project))["guidance"]
    assert list(WRITING_RULES) == guidance[-len(WRITING_RULES) :]
    assert any("an outcome someone else can check" in line for line in guidance)
    assert not set(SIZING_RULES) & set(guidance)


def test_scenario_specs_step_says_where_a_fact_goes(project: Workspace) -> None:
    """Requirement "Spec background": the specs step gives the four places a fact goes."""
    project.change(deltas={}, design=None, tasks=None)
    guidance = valid(at(project))["guidance"]
    assert FACT_RULE in guidance
    for place in ("requirement", "Background", "resource", "charter's Context"):
        assert place in FACT_RULE
    assert FACT_RULE not in at(project, "tasks")["guidance"]


def test_scenario_tasks_step(project: Workspace) -> None:
    project.change(tasks=None)
    guidance = valid(at(project))["guidance"]
    assert at(project)["step"] == "tasks"
    assert set(SIZING_RULES) <= set(guidance)
    assert any("run past about five bullets" in line for line in guidance)
    assert not set(WRITING_RULES) & set(guidance)
    assert not set(WRITING_RULES + SIZING_RULES) & set(at(project, "design")["guidance"])


def test_scenario_resource_item(project: Workspace) -> None:
    """Requirement "Writing and sizing rules": the tasks step asks for a resource item."""
    project.change(tasks=None)
    guidance = valid(at(project))["guidance"]
    rule = (
        "Give a change that sets up or alters something outside the repo an item to create or "
        "update its resource."
    )
    assert rule in guidance
    assert rule not in at(project, "specs")["guidance"]


ONE_ITEM = HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty\n  - Verify: a test\n"


def reviewable(project: Workspace, level: str = "independent") -> None:
    """A change with every item ticked, at the given review level."""
    project.change(
        proposal_text=proposal().replace(
            "Owner: Sam Doe\n", f"Owner: Sam Doe\n- Review: {level}\n"
        ),
        tasks=ONE_ITEM,
    )
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")


def test_scenario_review_pack(project: Workspace) -> None:
    """Requirement "Severity rubric": the review pack gives it."""
    reviewable(project)
    payload = pack(project, "review")
    assert payload["severity_rubric"] == list(SEVERITY_RUBRIC)
    assert payload["severity_rubric"][0].startswith(
        "critical: a criterion or scenario doesn't hold"
    )
    text = render.to_text(payload, PLAIN)
    assert text.index("## Severity rubric") < text.index("## How to finish")


def test_scenario_self_review(project: Workspace) -> None:
    reviewable(project, "self")
    payload = valid(at(project))
    assert payload["step"] == "review"
    assert payload["severity_rubric"] == list(SEVERITY_RUBRIC)
    assert "Severity rubric" in render.to_text(payload, PLAIN)
    assert at(project, "tasks")["severity_rubric"] == []


def test_scenario_implement_pack(project: Workspace) -> None:
    """Requirement "Stopping rules": the implement pack gives them."""
    accepted(project)
    payload = pack(project, "implement")
    assert payload["stopping_rules"] == list(STOPPING_RULES)
    assert any(
        "three attempts" in rule and "end with partial" in rule
        for rule in payload["stopping_rules"]
    )
    text = render.to_text(payload, PLAIN)
    assert text.index("## When to stop") < text.index("## How to finish")
    assert "severity_rubric" not in payload


def test_scenario_apply_has_no_checklist(project: Workspace) -> None:
    accepted(project)
    payload = valid(at(project))
    assert payload["step"] == "apply"
    assert payload["checklist"] == []


def test_scenario_shared_rules_at_every_step(project: Workspace) -> None:
    project.change("add-order", design=None, tasks=None)
    project.change(design=None, tasks=None)
    proposing = at(project, "propose")
    archiving = valid(instructions(project.record(), "archive", "add-order"))
    assert proposing["shared_rules"] == archiving["shared_rules"] == list(SHARED_RULES)
    assert any("Only the human accepts a change" in rule for rule in archiving["shared_rules"])
    explore = valid(instructions(project.record(), "explore", None))
    assert explore["shared_rules"] == list(SHARED_RULES)
    assert explore["checklist"] == []


def test_every_drafting_step_has_a_checklist_and_its_codes_exist() -> None:
    """Requirement "Checklist per drafting step": an enforced check names real codes."""
    source = "".join(
        path.read_text(encoding="utf-8")
        for path in Path(waymark.__file__).parent.joinpath("record").glob("*.py")
    )
    assert set(CHECKLISTS) == {StepKind.PROPOSE, StepKind.SPECS, StepKind.DESIGN, StepKind.TASKS}
    for checks in CHECKLISTS.values():
        assert any(check.enforced_by for check in checks)
        assert any(not check.enforced_by for check in checks)
        for check in checks:
            for code in check.enforced_by:
                assert f'"{code}"' in source, code


def test_instructions_carry_every_rule_at_every_step(project: Workspace) -> None:
    project.write("charter.md", RULES)
    accepted(project)
    for step in ("tasks", "apply", "review", "design"):
        assert at(project, step)["rules"] == ALL_RULES
    explore = valid(instructions(project.record(), "explore", None))
    assert explore["rules"] == ALL_RULES
    assert explore["change"] is None
    assert "wm context --for explore" in explore["commands"]


def test_instruction_templates_follow_the_formats_wm_parses(project: Workspace) -> None:
    project.change(design=None, tasks=None)
    design = at(project, "design")["outputs"][0]["template"]
    parsed_design = parse_design(Document.parse("design.md", design))
    assert {problem.code for problem in parsed_design.problems} == {"empty-section"}
    assert [decision.name for decision in parsed_design.decisions] == ["<name>"]
    tasks = at(project, "tasks")["outputs"][0]["template"]
    parsed = parse_tasks(Document.parse("tasks.md", tasks))
    assert parsed.problems == ()
    assert [item.number for item in parsed.items] == ["1.1", "1.2"]
    assert parsed.items[0].criteria is not None
    specs = at(project, "specs")["outputs"][0]["template"]
    parsed_delta = parse_delta("search", Document.parse("specs/search.md", specs))
    assert [item.name for item in parsed_delta.added] == ["<name>"]
    assert [item.name for item in parsed_delta.removed] == ["<name>"]
    assert {problem.code for problem in parsed_delta.problems} <= {
        "empty-section",
        "duplicate-requirement",
    }


def test_task_instructions_in_an_atlas_ask_for_a_repo_on_every_item(atlas: Workspace) -> None:
    atlas.change(tasks=None)
    step = valid(instructions(atlas.record(), "tasks", NAME))
    assert "  - Repo: <api | web>" in step["outputs"][0]["template"]
    assert any("Repo line" in line for line in step["guidance"])


def test_review_instructions_follow_the_changes_review_level(project: Workspace) -> None:
    project.change(
        proposal_text=proposal().replace(
            "Owner: Sam Doe\n", "Owner: Sam Doe\n- Review: independent\n"
        ),
        tasks=HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n",
    )
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    step = at(project)
    assert (step["step"], step["item"]) == ("review", None)
    assert step["commands"][0] == f"wm context {NAME} --for review"
    assert any("reviewer" in line for line in step["guidance"])
    assert any("CHANGE line" in line for line in step["guidance"])


def mentions_an_implementer(step: dict[str, Any]) -> bool:
    text = render.to_text(step, PLAIN) + render.to_json(step)
    return "implementer" in text.lower()


def test_apply_instructions_have_the_planner_build_an_untagged_item(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n")
    step = at(project)
    assert (step["step"], step["item"]) == ("apply", "1.1")
    assert step["commands"] == [
        f"wm context {NAME} 1.1 --for implement",
        f"wm tick {NAME} 1.1",
        f'wm block {NAME} 1.1 "<reason>"',
        f'wm gap {NAME} 1.1 "<what is missing>"',
    ]
    assert any("yourself" in line for line in step["guidance"])
    assert any("checks the item touches" in line for line in step["guidance"])
    assert not mentions_an_implementer(step)


def test_apply_instructions_delegate_a_tagged_item(project: Workspace) -> None:
    accepted(
        project,
        HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Build: delegate\n  - Criteria: fifty\n",
    )
    step = at(project)
    assert (step["step"], step["item"]) == ("apply", "1.1")
    assert step["commands"] == [f"wm context {NAME} 1.1 --for implement"]
    assert step["guidance"][0] == (
        "Start an implementer for item 1.1 with the change and item and nothing else."
    )


@pytest.mark.parametrize("tag", ["", "\n  - Build: delegate"])
def test_apply_instructions_reopen_an_item_after_a_changes_verdict(
    project: Workspace, tag: str
) -> None:
    accepted(project, HEAD + f"- [ ] 1.1 Cap it{tag}\n  - Verify: a test\n  - Criteria: fifty\n")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "off by one", DAY, items=["1.1"])
    step = at(project)
    assert (step["step"], step["item"]) == ("apply", "1.1")
    assert step["commands"][0] == f"wm reopen {NAME} 1.1"
    assert step["commands"][1] == f"wm context {NAME} 1.1 --for implement"
    assert mentions_an_implementer(step) == bool(tag)


def test_instructions_for_items_waiting_on_the_human_point_to_resolve(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n")
    lifecycle.block(project.root, NAME, "1.1", "waiting")
    step = at(project)
    assert (step["step"], step["item"]) == ("resolve-items", "1.1")
    assert step["commands"][0] == f'wm resolve {NAME} 1.1 "<what was decided>"'


def test_instructions_need_a_change_named_when_several_are_active(project: Workspace) -> None:
    with pytest.raises(Refusal, match="wm new change"):
        instructions(project.record(), None, None)
    project.change()
    assert instructions(project.record(), None, None)["change"] == NAME
    project.change("add-order", deltas={"search": delta(added=(requirement("Order"),))})
    with pytest.raises(Refusal, match="Active changes: add-limit, add-order"):
        instructions(project.record(), None, None)
    with pytest.raises(Refusal, match="no active change"):
        instructions(project.record(), None, "fix-typo")


def test_implementer_pack_holds_the_item_the_change_and_the_touched_requirements(
    project: Workspace,
) -> None:
    project.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    changed = requirement(statement="A search SHALL return at most twenty results.")
    accepted(project, deltas={"search": delta(modified=(changed,), added=(requirement("Order"),))})
    built = pack(project, "implement")
    assert built["for"] == "implement"
    assert built["item"]["number"] == "1.1"
    assert built["item"]["criteria"] == "at most fifty results come back"
    assert built["item"]["verify"] == "a test covers fifty-one matches"
    assert built["proposal"]["Why"] == "Long result lists are slow."
    assert "A search SHALL return at most twenty results." in built["deltas"][0]["text"]
    assert built["design"].startswith("# Design")
    assert [(r["spec"], r["name"]) for r in built["requirements"]] == [("search", "Result limit")]
    assert "at most fifty results" in built["requirements"][0]["text"]
    assert built["context"] == "The search index is rebuilt nightly."
    assert built["rules"] == CHARTER_RULES
    assert RESULT_LINE in built["ends_with"]
    text = render.to_text(built, PLAIN)
    assert text.startswith(f"# Context pack: implement {NAME} 1.1")
    assert "## Requirements as they stand today" in text


def test_reviewer_pack_holds_the_whole_change_but_not_how_it_was_built(
    project: Workspace,
) -> None:
    accepted(project, proposal_text=INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.add_note(project.root, NAME, "1.2", "took a shortcut through the cache", DAY)
    lifecycle.tick(project.root, NAME, "1.2")
    built = pack(project, "review")
    assert built["change"] == NAME
    assert built["review_level"] == "independent"
    assert [item["number"] for item in built["items"]] == ["1.1", "1.2"]
    assert built["items"][0]["criteria"] == "at most fifty results come back"
    assert built["items"][0]["verify"] == "a test covers fifty-one matches"
    assert "notes" not in built["items"][0]
    assert "proposal" not in built
    assert built["design"].startswith("# Design")
    assert "#### Scenario: Many matches" in built["deltas"][0]["text"]
    assert built["rules"] == CHARTER_RULES
    assert "CHANGE: <change>" in built["ends_with"]
    assert VERDICT_LINE in built["ends_with"]
    text = render.to_text(built, PLAIN)
    assert text.startswith(f"# Context pack: review {NAME}")
    assert "shortcut" not in text
    assert "Long result lists are slow" not in text


def test_reviewer_pack_carries_the_earlier_reviews_of_the_change(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(
        project.root,
        NAME,
        Verdict.CHANGES,
        "off by one",
        DAY,
        items=["1.1"],
        findings=["critical: src/search.py:12: fifty-one come back"],
    )
    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    built = pack(project, "review")
    assert built["review_level"] == "independent"
    assert built["reviews"] == [
        {
            "date": "2026-01-15",
            "verdict": "changes",
            "text": "off by one",
            "items": ["1.1"],
            "covers": ["1.1"],
            "findings": [
                {"severity": "critical", "place": "src/search.py:12", "text": "fifty-one come back"}
            ],
        }
    ]
    assert "critical: src/search.py:12" in render.to_text(built, PLAIN)


def test_implementer_pack_carries_earlier_notes_reviews_and_decisions(
    project: Workspace,
) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n")
    lifecycle.add_note(project.root, NAME, "1.1", "half done", DAY)
    lifecycle.block(project.root, NAME, "1.1", "which bound?")
    lifecycle.resolve(project.root, NAME, "1.1", "use an inclusive bound", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "off by one", DAY, items=["1.1"])
    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    item = pack(project, "implement")["item"]
    assert item["notes"] == ["half done"]
    assert item["resolutions"] == ["use an inclusive bound"]
    assert item["reviews"] == [
        {
            "date": "2026-01-15",
            "verdict": "changes",
            "text": "off by one",
            "items": ["1.1"],
            "covers": ["1.1"],
            "findings": [],
        }
    ]
    assert "review_level" not in item


def test_context_pack_for_an_unaccepted_change_is_refused(project: Workspace) -> None:
    project.change()
    assert "is not accepted" in refused(project, "implement")
    lifecycle.accept(project.root, NAME, DAY)
    project.replace(f"{FOLDER}/proposal.md", "Paging.", "Paging and sorting.")
    assert "was withdrawn" in refused(project, "implement")
    assert "was withdrawn" in refused(project, "review")


def test_context_pack_for_an_item_without_criteria_is_refused(project: Workspace) -> None:
    accepted(project)
    project.replace(f"{FOLDER}/tasks.md", "  - Criteria: the help text names the limit\n", "")
    assert 'acceptance of "add-limit" was withdrawn' in refused(project, "implement", "1.2")


def test_context_pack_is_refused_when_a_link_in_the_change_is_broken(project: Workspace) -> None:
    project.change(design=DESIGN.replace("after sorting.", "after [sorting](sort.md)."))
    lifecycle.accept(project.root, NAME, DAY)
    message = refused(project, "implement")
    assert f"{FOLDER}/design.md:9" in message
    assert "sort.md" in message


def test_context_pack_is_refused_when_a_delta_does_not_apply(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    accepted(project, deltas={"search": delta(added=(requirement("Result order"),))})
    project.write("specs/search.md", spec(requirement(), requirement("Result order")))
    assert "already has a requirement" in refused(project, "implement")


def test_context_pack_names_exactly_one_change_and_item(project: Workspace) -> None:
    accepted(project)
    record = project.record()
    for arguments in ((None, None), (NAME, None)):
        with pytest.raises(Refusal, match="exactly one change and one item"):
            context_pack(record, "implement", *arguments)
    with pytest.raises(Refusal, match=r"no item 9\.9"):
        context_pack(record, "implement", NAME, "9.9")
    for review_arguments in ((None, None), (NAME, "1.1")):
        with pytest.raises(Refusal, match="exactly one change and no item"):
            context_pack(record, "review", *review_arguments)
    with pytest.raises(Refusal, match="no active change"):
        context_pack(record, "review", "add-order")
    with pytest.raises(Refusal, match="takes no change or item"):
        context_pack(record, "explore", NAME, "1.1")


def test_implementer_pack_is_refused_for_an_item_that_is_done_or_waiting(
    project: Workspace,
) -> None:
    accepted(
        project,
        HEAD
        + (
            "- [ ] 1.1 A\n"
            "  - Verify: a test\n"
            "  - Criteria: a\n"
            "- [ ] 1.2 B\n"
            "  - Verify: a test\n"
            "  - Criteria: b\n"
        ),
    )
    lifecycle.block(project.root, NAME, "1.1", "waiting for wording")
    assert "waits on the human" in refused(project, "implement")
    lifecycle.tick(project.root, NAME, "1.2")
    assert "already ticked" in refused(project, "implement", "1.2")
    lifecycle.resolve(project.root, NAME, "1.1", "go ahead", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.CHANGES, "no", DAY, items=["1.2"])
    assert "Reopen it first" in refused(project, "implement", "1.2")


def test_reviewer_pack_is_refused_when_there_is_nothing_to_review(project: Workspace) -> None:
    accepted(project, proposal_text=INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "items still to build (1.2)" in refused(project, "review")
    lifecycle.tick(project.root, NAME, "1.2")
    lifecycle.verdict(project.root, NAME, Verdict.PASS, "fine", DAY)
    assert "already has the review it needs" in refused(project, "review")


def test_reviewer_pack_is_refused_below_independent(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    assert "no reviewer is started" in refused(project, "review")


def test_delegation_gate_passes_for_a_healthy_accepted_item(project: Workspace) -> None:
    accepted(project)
    record = project.record()
    change = record.changes[NAME]
    assert change.tasks is not None
    assert delegation_problems(record, change, change.tasks.items[0], "implement") == []


def test_pack_in_an_atlas_resolves_the_items_repo_to_its_folder_in_text_only(
    tmp_path: Any,
) -> None:
    from tests.conftest import git_init  # noqa: PLC0415 - only this test needs it

    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    atlas.change(
        tasks=HEAD
        + "- [ ] 1.1 Add the endpoint\n  - Verify: a test\n  - Criteria: fifty\n  - Repo: api\n"
    )
    lifecycle.accept(atlas.root, NAME, DAY)
    built = valid(context_pack(atlas.record(), "implement", NAME, "1.1"))
    assert built["item"]["repo"] == "api"
    assert built["item"]["repo_found"] is True
    folder = str((tmp_path / "suite-api").resolve())
    assert f"- Repo: api (its folder on this machine is {folder})" in render.to_text(built, PLAIN)
    assert folder not in render.to_json(built)
    assert '"repo_found": true' in render.to_json(built)


def test_delegation_gate_refuses_an_item_whose_repo_is_not_on_this_machine(
    tmp_path: Any,
) -> None:
    from tests.conftest import git_init  # noqa: PLC0415 - only this test needs it

    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    atlas.change(
        tasks=HEAD
        + "- [ ] 1.1 Add the endpoint\n  - Verify: a test\n  - Criteria: fifty\n  - Repo: api\n"
    )
    lifecycle.accept(atlas.root, NAME, DAY)
    with pytest.raises(Refusal, match=r'works in a repo that isn.t here.*"api"'):
        context_pack(atlas.record(), "implement", NAME, "1.1")


def test_explore_pack_holds_the_charter_and_an_index_of_the_record(project: Workspace) -> None:
    project.write("charter.md", RULES)
    project.write("specs/search.md", spec())
    project.change("add-order", deltas={"search": delta(added=(requirement("Order"),))})
    project.write(
        "explorations/paging.md",
        "# Paging\n\n- Status: parked\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\nlater\n\n## Related\n",
    )
    built = valid(context_pack(project.record(), "explore"))
    assert built["charter"]["Vision"] == "Fast search for everyone."
    assert built["rules"] == ALL_RULES
    assert built["specs"] == [
        {
            "name": "search",
            "title": "Search",
            "purpose": "How search behaves.",
            "requirements": ["Result limit"],
        }
    ]
    assert built["changes"] == [
        {"name": "add-order", "title": "Limit the results", "phase": "planned"}
    ]
    assert built["explorations"] == [
        {"name": "paging", "title": "Paging", "status": "parked", "detail": "later"}
    ]
    text = render.to_text(built, PLAIN)
    assert "## Vision" in text
    assert "- search: How search behaves. (Result limit)" in text


def test_context_packs_are_the_same_on_every_machine(project: Workspace) -> None:
    accepted(project)
    first = context_pack(project.record(), "implement", NAME, "1.1")
    assert first == context_pack(project.record(), "implement", NAME, "1.1")
    assert str(project.root) not in render.to_json(first)
    for relative in ("proposal.md", "design.md", "tasks.md", "specs/search.md"):
        path = f"{FOLDER}/{relative}"
        project.write(path, project.read(path).replace("\n", "\r\n"))
    assert context_pack(project.record(), "implement", NAME, "1.1") == first


def test_instructions_for_a_review_waiting_on_the_human_point_to_resolve(
    project: Workspace,
) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: fifty\n")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, Verdict.SPEC_GAP, "no scenario for zero", DAY)
    step = at(project)
    assert (step["step"], step["item"]) == ("resolve-items", None)
    assert step["commands"][0] == f'wm resolve {NAME} review "<what was decided>"'


def test_proposal_instructions_explain_the_review_line(project: Workspace) -> None:
    project.write(f"{FOLDER}/proposal.md", "# Limit\n\nOwner: Sam Doe\n")
    guidance = " ".join(at(project)["guidance"])
    assert '"- Review: self|independent|none"' in guidance
    assert "modifies or removes an existing requirement" in guidance


def test_built_and_reviewed(project: Workspace) -> None:
    accepted(project)
    for number in ("1.1", "1.2"):
        lifecycle.tick(project.root, NAME, number)
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    step = at(project)
    assert step["step"] == "archive"
    guidance = " ".join(step["guidance"])
    assert "archive on the change's branch, before the pull request" in guidance
    assert "merge" not in guidance.lower()
    assert "merge" not in step["unlocks"].lower()


def test_specs_instructions_ask_for_functional_requirements(project: Workspace) -> None:
    project.write(f"{FOLDER}/proposal.md", proposal())
    step = at(project)
    assert step["step"] == "specs"
    assert any(
        "as a user or another program sees it" in line
        and "internals and mechanisms go in the design" in line
        for line in step["guidance"]
    )


def test_reviewer_pack_holds_only_the_items_added_after_a_pass(project: Workspace) -> None:
    accepted(project, proposal_text=INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    lifecycle.verdict(project.root, NAME, Verdict.PASS, "fine", DAY, by="wm-reviewer")
    assert "already has the review it needs" in refused(project, "review")
    project.replace(
        f"{FOLDER}/tasks.md",
        "  - Verify: read the help text\n",
        "  - Verify: read the help text\n"
        "- [ ] 1.3 Name it\n  - Criteria: named\n  - Verify: a test\n",
    )
    lifecycle.tick(project.root, NAME, "1.3")
    built = pack(project, "review")
    assert built["uncovered_only"] is True
    assert [item["number"] for item in built["items"]] == ["1.3"]
    assert [(review["verdict"], review["covers"]) for review in built["reviews"]] == [
        ("pass", ["1.1", "1.2"])
    ]
    assert built["deltas"]
    assert built["design"]
    text = render.to_text(built, PLAIN)
    assert "Review only the items below, at level independent" in text
    assert "- Earlier review (2026-01-15, pass, covers 1.1 1.2): fine" in text
    assert "Cap the result count" not in text


def test_reviewer_pack_holds_every_item_for_a_first_review(project: Workspace) -> None:
    accepted(project, proposal_text=INDEPENDENT)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    built = pack(project, "review")
    assert built["uncovered_only"] is False
    assert [item["number"] for item in built["items"]] == ["1.1", "1.2"]
    assert "Review the whole change at level independent" in render.to_text(built, PLAIN)


def member_of_faster_search(project: Workspace) -> None:
    """An independently reviewed change that belongs to the milestone faster-search."""
    project.change(
        proposal_text=INDEPENDENT.replace(
            "- Owner: Sam Doe\n", "- Owner: Sam Doe\n- Milestone: faster-search\n"
        )
    )
    project.write(
        "milestones/faster-search/milestone.md",
        milestone("- [add-limit](../../changes/add-limit/proposal.md): cap the results\n"),
    )
    lifecycle.accept(project.root, NAME, DAY)


def test_scenario_member_changes_packs(project: Workspace) -> None:
    """Requirement "Milestone in the context packs"."""
    member_of_faster_search(project)
    expected = {"name": "faster-search", "goal": "Answers in a blink.", "non_goals": "Ranking."}
    built = pack(project, "implement")
    assert built["milestone"] == expected
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    reviewed = pack(project, "review")
    assert reviewed["milestone"] == expected
    for payload in (built, reviewed):
        text = render.to_text(payload, PLAIN)
        assert "## Milestone\n\nThis change works toward `faster-search`." in text
        assert "### Goal\n\nAnswers in a blink." in text
        assert "### Non-goals\n\nRanking." in text
        assert "P95 is low" not in text
        assert "cap the results" not in text


def test_scenario_change_without_a_milestone(project: Workspace) -> None:
    accepted(project)
    built = pack(project, "implement")
    assert built["milestone"] is None
    assert "## Milestone" not in render.to_text(built, PLAIN)


def comes_after(other: str) -> str:
    return proposal().replace("- Owner: Sam Doe\n", f"- Owner: Sam Doe\n- After: {other}\n")


def test_scenario_change_without_a_dependency_in_the_instructions(project: Workspace) -> None:
    """Requirement "Branch and base": a change without `- After:` is based on main."""
    project.change()
    payload = valid(instructions(project.record(), None, NAME))
    assert (payload["branch"], payload["base"]) == (NAME, "main")
    assert f"Branch {NAME}, based on main." in render.to_text(payload, PLAIN)


def test_scenario_stacked_change_in_the_instructions(project: Workspace) -> None:
    project.change()
    project.change("add-paging", proposal_text=comes_after(NAME))
    payload = valid(instructions(project.record(), None, "add-paging"))
    assert (payload["branch"], payload["base"]) == ("add-paging", NAME)
    assert f"Branch add-paging, based on {NAME}." in render.to_text(payload, PLAIN)


def test_scenario_dependency_merged_in_the_instructions(project: Workspace) -> None:
    project.write(f"changes/archive/2026-01-20-{NAME}/proposal.md", proposal(outcome="Done."))
    project.change("add-paging", proposal_text=comes_after(NAME))
    payload = valid(instructions(project.record(), None, "add-paging"))
    assert payload["base"] == "main"


def test_explore_instructions_have_no_branch(project: Workspace) -> None:
    payload = valid(instructions(project.record(), "explore", None))
    assert (payload["branch"], payload["base"]) == (None, None)


def a_resource(title: str, serves: str, status: str = "active") -> str:
    return (
        f"# {title}\n\n- Kind: service\n- Serves: {serves}\n- Status: {status}\n"
        "- Verified: 2026-11-17\n\n"
        f"## What it is\n\n{title} takes payments.\n\n"
        f"## Access\n\nThe key is in the vault item {title}.\n\n"
        "## Interface\n\nNone.\n\n## Data\n\nNone.\n\n"
        "## Configuration\n\n### dev\n\nTest mode, secret settings.\n\n### prod\n\nLive mode.\n\n"
        "## Verification\n\nA test charge.\n"
    )


def billing_change(project: Workspace, *, independent: bool = False) -> Workspace:
    """An accepted change with a delta for the spec billing."""
    project.write("specs/billing.md", spec(title="Billing", purpose="How billing behaves."))
    project.write("specs/notifications.md", spec(title="Notifications", purpose="Mail."))
    impact = "- Specs: `billing`\n- User-visible: refunds\n- Code: billing\n"
    text = proposal(impact=impact)
    if independent:
        text = text.replace("- Owner: Sam Doe\n", "- Owner: Sam Doe\n- Review: independent\n")
    return accepted(
        project,
        proposal_text=text,
        deltas={"billing": delta(title="Billing", added=(requirement("Refunds"),))},
    )


def test_scenario_serving_resource_in_the_implement_pack(project: Workspace) -> None:
    """Requirement "Resources in context packs"."""
    billing_change(project)
    project.write("resources/stripe.md", a_resource("Stripe", "billing"))
    built = pack(project, "implement")
    [stripe] = built["resources"]
    assert (stripe["name"], stripe["kind"]) == ("stripe", "service")
    assert stripe["what_it_is"] == "Stripe takes payments."
    assert stripe["access"] == "The key is in the vault item Stripe."
    titles = [heading["title"] for heading in stripe["outline"]]
    assert {"Configuration", "dev", "prod"} <= set(titles)
    assert "What it is" not in titles
    assert stripe["command"] == "wm show stripe --kind resource"
    text = render.to_text(built, PLAIN)
    assert "Stripe takes payments." in text
    assert "wm show stripe --kind resource" in text
    assert "secret settings" not in text


def test_scenario_resource_for_another_spec(project: Workspace) -> None:
    billing_change(project)
    project.write("resources/mailgun.md", a_resource("Mailgun", "notifications"))
    built = pack(project, "implement")
    assert built["resources"] == []
    assert "mailgun" not in render.to_text(built, PLAIN).casefold()


def test_scenario_retired_resource(project: Workspace) -> None:
    billing_change(project, independent=True)
    project.write("resources/heroku.md", a_resource("Heroku", "billing", "retired"))
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    built = pack(project, "review")
    assert built["resources"] == []
    assert "heroku" not in render.to_text(built, PLAIN).casefold()


def with_background(text: str, background: str) -> str:
    return text.replace("## Requirements", f"## Background\n\n{background}\n\n## Requirements")


def test_scenario_background_of_a_touched_spec(project: Workspace) -> None:
    """Requirement "Background in the packs": only the specs the change has a delta for."""
    billing_change(project)
    billing = spec(title="Billing", purpose="How billing behaves.")
    mail = spec(title="Notifications", purpose="Mail.")
    project.write("specs/billing.md", with_background(billing, "Invoices go out monthly."))
    project.write("specs/notifications.md", with_background(mail, "Mail goes through Mailgun."))
    built = pack(project, "implement")
    assert built["backgrounds"] == [{"spec": "billing", "text": "Invoices go out monthly."}]
    text = render.to_text(built, PLAIN)
    assert "### billing\n\nInvoices go out monthly." in text
    assert "Mailgun" not in text


def test_scenario_background_from_the_delta(project: Workspace) -> None:
    project.write(
        "specs/billing.md",
        with_background(spec(title="Billing", purpose="How billing."), "Invoices go out monthly."),
    )
    impact = "- Specs: `billing`\n- User-visible: refunds\n- Code: billing\n"
    text = proposal(impact=impact).replace(
        "- Owner: Sam Doe\n", "- Owner: Sam Doe\n- Review: independent\n"
    )
    added = delta(title="Billing", added=(requirement("Refunds"),))
    added = added.replace("## ADDED", "## Background\n\nInvoices go out weekly.\n\n## ADDED")
    accepted(project, proposal_text=text, deltas={"billing": added})
    weekly = [{"spec": "billing", "text": "Invoices go out weekly."}]
    assert pack(project, "implement")["backgrounds"] == weekly
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.tick(project.root, NAME, "1.2")
    built = pack(project, "review")
    assert built["backgrounds"] == weekly
    text = render.to_text(built, PLAIN)
    assert "### billing\n\nInvoices go out weekly." in text
    assert "monthly" not in text


def test_specs_with_no_background_leave_the_packs_without_one(project: Workspace) -> None:
    billing_change(project)
    built = pack(project, "implement")
    assert built["backgrounds"] == []
    assert "## Background" not in render.to_text(built, PLAIN)


def test_scenario_explore_index(project: Workspace) -> None:
    project.write("specs/billing.md", spec(title="Billing", purpose="How billing behaves."))
    project.write("resources/stripe.md", a_resource("Stripe", "billing"))
    project.write("resources/heroku.md", a_resource("Heroku", "none", "retired"))
    built = valid(context_pack(project.record(), "explore"))
    assert built["resources"] == [
        {
            "name": "heroku",
            "title": "Heroku",
            "kind": "service",
            "status": "retired",
            "serves": [],
        },
        {
            "name": "stripe",
            "title": "Stripe",
            "kind": "service",
            "status": "active",
            "serves": ["billing"],
        },
    ]
    text = render.to_text(built, PLAIN)
    assert "- heroku (service, retired, serves none): Heroku" in text
    assert "- stripe (service, active, serves billing): Stripe" in text

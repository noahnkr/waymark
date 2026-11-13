"""The agent interface: instructions for each step, and context packs for each job."""

import datetime
import json
from typing import Any

import pytest

from tests.support import (
    ATLAS_CONFIG,
    CHARTER,
    DESIGN,
    TASKS,
    Workspace,
    delta,
    proposal,
    requirement,
    spec,
)
from tests.views.validator import errors
from waymark.record.deltas import parse_delta
from waymark.record.design import parse_design
from waymark.record.tasks import parse_tasks
from waymark.record.terms import Verdict
from waymark.record.text import Document
from waymark.services import lifecycle
from waymark.services.common import Refusal
from waymark.services.context import RESULT_LINE, VERDICT_LINE, context_pack, delegation_problems
from waymark.services.instructions import instructions
from waymark.views import render
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

NAME = "add-limit"
FOLDER = f"changes/{NAME}"
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
PLAIN = Style()
RULES = CHARTER + "\n### tasks\n\nKeep items small.\n\n### explore\n\nAsk before assuming.\n"


def valid(payload: dict[str, Any]) -> dict[str, Any]:
    name = payload["schema"].removeprefix("wm.")
    assert errors(render.public(payload), SCHEMAS[name]) == []
    assert json.loads(render.to_json(payload)) == render.public(payload)
    assert render.to_text(payload, PLAIN)
    return payload


def at(project: Workspace, step: str | None = None) -> dict[str, Any]:
    return valid(instructions(project.record(), step, NAME))


def pack(project: Workspace, role: str, number: str = "1.1") -> dict[str, Any]:
    return valid(context_pack(project.record(), role, NAME, number))


def refused(project: Workspace, role: str, number: str = "1.1") -> str:
    with pytest.raises(Refusal) as refusal:
        context_pack(project.record(), role, NAME, number)
    return str(refusal.value)


def accepted(project: Workspace, tasks: str = TASKS, **options: Any) -> Workspace:
    project.change(tasks=tasks, **options)
    lifecycle.accept(project.root, NAME, DAY)
    return project


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
    assert step["commands"] == [f"wm context {NAME} 1.1 --for implement"]

    lifecycle.tick(project.root, NAME, "1.1")
    step = at(project)
    assert (step["step"], step["item"]) == ("review", "1.1")
    assert step["commands"] == [f'wm review {NAME} 1.1 --self "<summary>"']

    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    assert (at(project)["step"], at(project)["item"]) == ("apply", "1.2")

    lifecycle.tick(project.root, NAME, "1.2")
    step = at(project)
    assert step["step"] == "archive"
    assert step["commands"] == [f'wm archive {NAME} --outcome "<what came of it>"']


def test_instructions_skip_the_design_on_the_short_path(project: Workspace) -> None:
    project.change(proposal_text=proposal(short=True), design=None, tasks=None)
    assert at(project)["step"] == "tasks"
    design = at(project, "design")
    assert not design["ready"]
    assert "short path" in design["reason"]
    assert any("short path" in line for line in at(project, "tasks")["guidance"])


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


def test_instructions_carry_only_the_rules_of_their_step(project: Workspace) -> None:
    project.write("charter.md", RULES)
    accepted(project)
    assert at(project, "tasks")["rules"] == "Keep items small."
    assert at(project, "apply")["rules"] == "Run the tests before reporting."
    assert at(project, "review")["rules"] == "Check every scenario."
    assert at(project, "design")["rules"] == ""
    for step in ("tasks", "apply", "review"):
        assert at(project, step)["context"] == "The search index is rebuilt nightly."
    explore = valid(instructions(project.record(), "explore", None))
    assert explore["rules"] == "Ask before assuming."
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


def test_review_instructions_follow_the_items_review_level(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it   `review: independent`\n  - Criteria: fifty\n")
    lifecycle.tick(project.root, NAME, "1.1")
    step = at(project)
    assert step["step"] == "review"
    assert step["commands"][0] == f"wm context {NAME} 1.1 --for review"
    assert any("reviewer" in line for line in step["guidance"])


def test_apply_instructions_reopen_an_item_after_a_changes_verdict(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty\n")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "off by one", DAY)
    step = at(project)
    assert (step["step"], step["item"]) == ("apply", "1.1")
    assert step["commands"][0] == f"wm reopen {NAME} 1.1"


def test_instructions_for_items_waiting_on_the_human_point_to_resolve(project: Workspace) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty\n")
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
    assert built["rules"] == "Run the tests before reporting."
    assert RESULT_LINE in built["ends_with"]
    text = render.to_text(built, PLAIN)
    assert text.startswith(f"# Context pack: implement {NAME} 1.1")
    assert "## Requirements as they stand today" in text


def test_reviewer_pack_leaves_out_how_the_item_was_built(project: Workspace) -> None:
    accepted(project)
    lifecycle.tick(project.root, NAME, "1.1")
    project.replace(
        f"{FOLDER}/tasks.md",
        "fifty-one matches\n",
        "fifty-one matches\n  - Note: took a shortcut through the cache\n",
    )
    built = pack(project, "review")
    assert built["item"]["criteria"] == "at most fifty results come back"
    assert built["item"]["verify"] == "a test covers fifty-one matches"
    assert built["item"]["notes"] == []
    assert built["proposal"] is None
    assert built["design"] is None
    assert built["requirements"] == []
    assert "#### Scenario: Many matches" in built["deltas"][0]["text"]
    assert built["rules"] == "Check every scenario."
    assert VERDICT_LINE in built["ends_with"]
    text = render.to_text(built, PLAIN)
    assert "shortcut" not in text
    assert "Cut the result list after sorting" not in text


def test_implementer_pack_carries_earlier_notes_reviews_and_decisions(
    project: Workspace,
) -> None:
    accepted(project, HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty\n  - Note: half done\n")
    lifecycle.block(project.root, NAME, "1.1", "which bound?")
    lifecycle.resolve(project.root, NAME, "1.1", "use an inclusive bound", DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.verdict(project.root, NAME, "1.1", Verdict.CHANGES, "off by one", DAY)
    lifecycle.reopen(project.root, NAME, "1.1", DAY)
    item = pack(project, "implement")["item"]
    assert item["notes"] == ["half done"]
    assert item["resolutions"] == ["use an inclusive bound"]
    assert item["reviews"] == [{"date": "2026-01-15", "verdict": "changes", "text": "off by one"}]
    assert item["review_level"] == "independent"


def test_context_pack_for_an_unaccepted_change_is_refused(project: Workspace) -> None:
    project.change()
    assert "is not accepted" in refused(project, "implement")
    lifecycle.accept(project.root, NAME, DAY)
    project.replace(f"{FOLDER}/proposal.md", "Paging.", "Paging and sorting.")
    assert "was withdrawn" in refused(project, "implement")
    assert "was withdrawn" in refused(project, "review")


def test_context_pack_for_an_item_without_criteria_is_refused(project: Workspace) -> None:
    accepted(project)
    assert "Item 1.2 has no criteria" in refused(project, "implement", "1.2")


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
    with pytest.raises(Refusal, match="no active change"):
        context_pack(record, "review", "add-order", "1.1")
    with pytest.raises(Refusal, match="takes no change or item"):
        context_pack(record, "explore", NAME, "1.1")


def test_implementer_pack_is_refused_for_an_item_that_is_done_or_waiting(
    project: Workspace,
) -> None:
    accepted(project, HEAD + "- [ ] 1.1 A\n  - Criteria: a\n- [ ] 1.2 B\n  - Criteria: b\n")
    lifecycle.block(project.root, NAME, "1.1", "waiting for wording")
    assert "waits on the human" in refused(project, "implement")
    lifecycle.tick(project.root, NAME, "1.2")
    assert "already ticked" in refused(project, "implement", "1.2")
    lifecycle.verdict(project.root, NAME, "1.2", Verdict.CHANGES, "no", DAY)
    assert "Reopen it first" in refused(project, "implement", "1.2")


def test_reviewer_pack_is_refused_when_there_is_nothing_to_review(project: Workspace) -> None:
    accepted(project)
    assert "isn't ticked yet" in refused(project, "review")
    lifecycle.tick(project.root, NAME, "1.1")
    lifecycle.self_review(project.root, NAME, "1.1", "fine", DAY)
    assert "already has the review record" in refused(project, "review")
    lifecycle.tick(project.root, NAME, "1.2")
    project.replace(f"{FOLDER}/tasks.md", "`review: none`\n", "`review: none`\n  - Criteria: x\n")
    lifecycle.accept(project.root, NAME, DAY)
    assert "needs no review" in refused(project, "review", "1.2")


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
    atlas.change(tasks=HEAD + "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty\n  - Repo: api\n")
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
    atlas.change(tasks=HEAD + "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty\n  - Repo: api\n")
    lifecycle.accept(atlas.root, NAME, DAY)
    with pytest.raises(Refusal, match=r'works in a repo that isn.t here.*"api"'):
        context_pack(atlas.record(), "implement", NAME, "1.1")


def test_explore_pack_holds_the_charter_and_an_index_of_the_record(project: Workspace) -> None:
    project.write("charter.md", RULES)
    project.write("specs/search.md", spec())
    project.change("add-order", deltas={"search": delta(added=(requirement("Order"),))})
    project.write(
        "explorations/paging.md",
        "# Paging\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\nParked: later\n\n## Related\n",
    )
    built = valid(context_pack(project.record(), "explore"))
    assert built["charter"]["Vision"] == "Fast search for everyone."
    assert built["rules"] == "Ask before assuming."
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

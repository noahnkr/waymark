"""The acceptance fingerprint: what withdraws acceptance, and what doesn't."""

import pytest

from tests.support import TASKS, Workspace, delta, requirement, spec
from waymark.record.deltas import merge_delta
from waymark.record.state import AcceptanceState

CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def accepted(workspace: Workspace) -> Workspace:
    workspace.change()
    workspace.accept()
    assert workspace.change_state().acceptance is AcceptanceState.VALID
    return workspace


def acceptance(workspace: Workspace, name: str = "add-limit") -> AcceptanceState:
    return workspace.change_state(name).acceptance


def test_change_without_an_acceptance_line_is_not_accepted(workspace: Workspace) -> None:
    workspace.change()
    assert acceptance(workspace) is AcceptanceState.MISSING


def test_acceptance_is_valid_while_the_change_is_as_accepted(workspace: Workspace) -> None:
    assert acceptance(accepted(workspace)) is AcceptanceState.VALID


def test_editing_the_proposal_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).replace("changes/add-limit/proposal.md", "Paging.", "Paging and sorting.")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_editing_a_delta_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).replace("changes/add-limit/specs/search.md", "fifty", "forty")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_adding_a_delta_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).write(
        "changes/add-limit/specs/export.md",
        delta(title="Export", added=(requirement(),), purpose="How export behaves."),
    )
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_editing_the_design_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).replace("changes/add-limit/design.md", "after sorting.", "before sorting.")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Cap the result count", "Cap the result count at fifty"),
        ("Criteria: at most fifty", "Criteria: at most forty"),
        ("Verify: a test covers", "Verify: nobody checks"),
        ("1.2 Document the limit   `review: none`", "1.2 Document the limit"),
        ("- [ ] 1.1 Cap the result count", "- [ ] 1.1 Cap the result count   `review: none`"),
    ],
)
def test_changing_an_item_definition_withdraws_acceptance(
    workspace: Workspace, old: str, new: str
) -> None:
    accepted(workspace).replace("changes/add-limit/tasks.md", old, new)
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_appending_an_item_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).write("changes/add-limit/tasks.md", TASKS + "- [ ] 1.3 Announce it\n")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_changing_the_default_review_level_withdraws_acceptance(workspace: Workspace) -> None:
    accepted(workspace).replace("config.toml", 'default_review = "self"', 'default_review = "none"')
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_ticks_blockers_review_records_and_notes_keep_acceptance(workspace: Workspace) -> None:
    accepted(workspace)
    tasks = "changes/add-limit/tasks.md"
    workspace.replace(tasks, "- [ ] 1.1", "- [x] 1.1")
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace(
        tasks,
        "  - Verify: a test covers fifty-one matches\n",
        "  - Verify: a test covers fifty-one matches\n"
        "  - Note: the cap sits after sorting\n"
        "  - (self-review) 2026-01-16: matches the criteria\n",
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace(
        tasks, "`review: none`\n", "`review: none`\n  - Blocked: waiting for wording\n"
    )
    assert acceptance(workspace) is AcceptanceState.VALID


def test_writing_the_outcome_keeps_acceptance(workspace: Workspace) -> None:
    accepted(workspace)
    text = workspace.read("changes/add-limit/proposal.md")
    workspace.write("changes/add-limit/proposal.md", text + "\n## Outcome\n\nShipped as planned.\n")
    assert acceptance(workspace) is AcceptanceState.VALID


def test_line_endings_do_not_change_the_fingerprint(workspace: Workspace) -> None:
    accepted(workspace)
    for name in ("proposal.md", "design.md", "tasks.md", "specs/search.md"):
        relative = f"changes/add-limit/{name}"
        workspace.write(relative, workspace.read(relative).replace("\n", "\r\n"))
    assert acceptance(workspace) is AcceptanceState.VALID


def test_tampered_fingerprint_is_not_a_valid_acceptance(workspace: Workspace) -> None:
    accepted(workspace)
    text = workspace.read("changes/add-limit/proposal.md")
    start = text.index("(fingerprint: ") + len("(fingerprint: ")
    workspace.write(
        "changes/add-limit/proposal.md", text[:start] + "0000000000000000" + text[start + 16 :]
    )
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_another_change_archiving_into_the_same_requirement_withdraws_acceptance(
    workspace: Workspace,
) -> None:
    workspace.write("specs/search.md", spec())
    workspace.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    workspace.accept("fix-limit")
    assert acceptance(workspace, "fix-limit") is AcceptanceState.VALID

    other = requirement(statement="A search SHALL return at most ten results.")
    workspace.write("changes/cut-limit/specs/search.md", delta(modified=(other,)))
    record = workspace.record()
    merged = merge_delta(record.specs["search"], record.changes["cut-limit"].deltas["search"])
    assert merged.text is not None
    workspace.write("specs/search.md", merged.text)
    workspace.path("changes/cut-limit/specs/search.md").unlink()

    assert acceptance(workspace, "fix-limit") is AcceptanceState.WITHDRAWN


def test_a_spec_changing_elsewhere_keeps_acceptance(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    workspace.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    workspace.accept("fix-limit")
    workspace.replace(
        "specs/search.md",
        "### Requirement: Empty query\nA search",
        "### Requirement: Empty query\nEvery search",
    )
    assert acceptance(workspace, "fix-limit") is AcceptanceState.VALID

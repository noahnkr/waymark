"""The acceptance fingerprint: what withdraws acceptance, and what doesn't."""

import pytest

from tests.support import TASKS, Workspace, delta, proposal, requirement, spec
from waymark.record.artifacts.deltas import merge_delta
from waymark.record.evidence.fingerprint import change_fingerprint
from waymark.record.state import AcceptanceState, StepKind

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
        ("**Criteria:** at most fifty", "**Criteria:** at most forty"),
        ("**Verify:** a test covers", "**Verify:** nobody checks"),
        ("1.2 Document the limit", "1.2 Document the limit in the guide"),
        (
            "- [ ] 1.1 Cap the result count\n"
            "  - **Criteria:** at most fifty results come back\n"
            "  - **Verify:** a test covers fifty-one matches\n",
            "- [ ] 1.1 Cap the result count\n"
            "  - **Criteria:** at most fifty results come back\n"
            "  - **Verify:** a test covers fifty-one matches\n"
            "  - **Build:** delegate\n",
        ),
    ],
)
def test_changing_an_item_definition_withdraws_acceptance(
    workspace: Workspace, old: str, new: str
) -> None:
    accepted(workspace).replace("changes/add-limit/tasks.md", old, new)
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_tag_added_after_acceptance_withdraws_it(workspace: Workspace) -> None:
    accepted(workspace).replace(
        "changes/add-limit/tasks.md",
        "1.2 Document the limit\n",
        "1.2 Document the limit\n  - **Build:** delegate\n",
    )
    state = workspace.change_state()
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert state.next_step.kind is StepKind.ACCEPT
    assert state.next_step.human


def test_removing_the_build_tag_withdraws_acceptance(workspace: Workspace) -> None:
    workspace.change(
        tasks=TASKS.replace(
            "1.2 Document the limit\n", "1.2 Document the limit\n  - **Build:** delegate\n"
        )
    )
    workspace.accept()
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace("changes/add-limit/tasks.md", "  - **Build:** delegate\n", "")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_fingerprint_of_a_plain_change_is_stable(workspace: Workspace) -> None:
    workspace.change()
    record = workspace.record()
    fingerprint = change_fingerprint(
        record.changes["add-limit"], record.specs, record.default_review
    )
    assert fingerprint == change_fingerprint(
        workspace.record().changes["add-limit"], record.specs, record.default_review
    )
    assert len(fingerprint) == 16


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("**Owner:** Sam Doe\n", "**Owner:** Sam Doe\n- **Review:** independent\n"),
        ("**Owner:** Sam Doe\n", "**Owner:** Sam Doe\n- **Review:** self\n"),
    ],
)
def test_adding_a_review_line_withdraws_acceptance(
    workspace: Workspace, old: str, new: str
) -> None:
    accepted(workspace).replace("changes/add-limit/proposal.md", old, new)
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_item_added(workspace: Workspace) -> None:
    accepted(workspace).write_tasks(
        TASKS + "- [ ] 1.3 Announce it\n  - **Verify:** a test\n  - **Criteria:** posted\n"
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    tasks = "changes/add-limit/tasks.md"
    workspace.replace(tasks, "- [ ] 1.1", "- [x] 1.1")
    workspace.replace(tasks, "- [ ] 1.2", "- [x] 1.2")
    step = workspace.change_state().next_step
    assert (step.kind, step.item) == (StepKind.APPLY, "1.3")


def test_accepted_item_edited(workspace: Workspace) -> None:
    accepted(workspace).replace(
        "changes/add-limit/tasks.md", "1.2 Document the limit", "1.2 Document the cap"
    )
    state = workspace.change_state()
    assert state.acceptance is AcceptanceState.WITHDRAWN
    assert (state.next_step.kind, state.next_step.human) == (StepKind.ACCEPT, True)


def test_accepted_item_removed(workspace: Workspace) -> None:
    accepted(workspace).write_tasks(TASKS.split("- [ ] 1.2", maxsplit=1)[0])
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_listing_every_item_fingerprints_like_no_list_but_for_order(workspace: Workspace) -> None:
    workspace.change()
    record = workspace.record()
    change = record.changes["add-limit"]
    every = change_fingerprint(change, record.specs, record.default_review)
    listed = change_fingerprint(change, record.specs, record.default_review, ["1.1", "1.2"])
    assert every == listed
    assert listed != change_fingerprint(change, record.specs, record.default_review, ["1.1"])


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
        "  - **Verify:** a test covers fifty-one matches\n",
        "  - **Verify:** a test covers fifty-one matches\n"
        "  - 2026-01-16 (note) by Sam Doe: the cap sits after sorting\n",
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace(
        tasks,
        "1.2 Document the limit\n",
        "1.2 Document the limit\n  - 2026-01-16 (blocked) by Sam Doe: waiting for wording\n",
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.write(
        tasks,
        workspace.read(tasks) + "- 2026-01-17 (self-review) by Sam Doe: fine\n",
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    assert workspace.record().changes["add-limit"].problems == ()
    assert [r.kind.value for r in workspace.record().changes["add-limit"].tasks.log] == [  # type: ignore[union-attr]
        "accepted",
        "self-review",
    ]


def test_writing_the_outcome_keeps_acceptance(workspace: Workspace) -> None:
    accepted(workspace)
    text = workspace.read("changes/add-limit/proposal.md")
    workspace.write("changes/add-limit/proposal.md", text + "\n## Outcome\n\nShipped as planned.\n")
    assert acceptance(workspace) is AcceptanceState.VALID


def test_a_comment_edited_after_acceptance_keeps_it(workspace: Workspace) -> None:
    """Requirement "Template examples": comments are left out of the fingerprint."""
    workspace.change(
        proposal_text=proposal().replace("## Why\n\n", "## Why\n\n<!-- Good: x. -->\n\n")
    )
    workspace.accept()
    workspace.replace(
        "changes/add-limit/proposal.md", "<!-- Good: x. -->", "<!-- Good: y.\nBad: z. -->"
    )
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace("changes/add-limit/proposal.md", "<!-- Good: y.\nBad: z. -->\n\n", "")
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.replace(
        "changes/add-limit/proposal.md", "Long result lists", "Very long result lists"
    )
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_a_comment_opener_in_inline_code_is_not_a_comment(workspace: Workspace) -> None:
    mention = "## Why\n\nA spec says `<!--` starts a comment.\n\n"
    workspace.change(proposal_text=proposal().replace("## Why\n\n", mention))
    workspace.accept()
    workspace.replace(
        "changes/add-limit/proposal.md", "Long result lists", "Very long result lists"
    )
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_a_comment_inside_fenced_code_still_counts(workspace: Workspace) -> None:
    fenced = "## Why\n\n```html\n<!-- a -->\n```\n\n"
    workspace.change(proposal_text=proposal().replace("## Why\n\n", fenced))
    workspace.accept()
    workspace.replace("changes/add-limit/proposal.md", "<!-- a -->", "<!-- b -->")
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN


def test_line_endings_do_not_change_the_fingerprint(workspace: Workspace) -> None:
    accepted(workspace)
    for name in ("proposal.md", "design.md", "tasks.md", "specs/search.md"):
        relative = f"changes/add-limit/{name}"
        workspace.write(relative, workspace.read(relative).replace("\n", "\r\n"))
    assert acceptance(workspace) is AcceptanceState.VALID


def test_tampered_fingerprint_is_not_a_valid_acceptance(workspace: Workspace) -> None:
    accepted(workspace)
    text = workspace.read("changes/add-limit/tasks.md")
    start = text.index(" fingerprint ") + len(" fingerprint ")
    workspace.write(
        "changes/add-limit/tasks.md", text[:start] + "0000000000000000" + text[start + 16 :]
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


def test_the_spec_text_of_a_renamed_requirement_is_covered(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec(requirement("Result cap")))
    rename = (
        "# Search\n\n## RENAMED Requirements\n\n- **From:** Result cap\n- **To:** Result limit\n"
    )
    workspace.change(deltas={"search": rename})
    workspace.accept()
    assert acceptance(workspace) is AcceptanceState.VALID
    workspace.write(
        "specs/search.md",
        spec(requirement("Result cap", statement="A search SHALL return at most ten results.")),
    )
    assert acceptance(workspace) is AcceptanceState.WITHDRAWN

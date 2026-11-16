"""wm check --fix: the standard layout, and what a fix never changes."""

import datetime

import pytest

from tests.support import DESIGN, TASKS, Workspace, proposal
from waymark.record.layout import Fix
from waymark.record.state import AcceptanceState
from waymark.services import fix, lifecycle
from waymark.services.common import Refusal
from waymark.services.fix import FixedFile, fix_layout

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
PROPOSAL_FILE = f"changes/{NAME}/proposal.md"
DESIGN_FILE = f"changes/{NAME}/design.md"
TASKS_FILE = f"changes/{NAME}/tasks.md"


def test_scenario_layout_fixed(project: Workspace) -> None:
    untidy = proposal().replace(
        "Search returns a capped list.", "* Search returns a capped list.  "
    )
    project.change(proposal_text=untidy)
    fixed = fix_layout(project.root)
    assert fixed == (FixedFile(PROPOSAL_FILE, (Fix.LIST_MARKERS, Fix.TRAILING_SPACES)),)
    assert project.read(PROPOSAL_FILE) == untidy.replace(
        "* Search returns a capped list.  ", "- Search returns a capped list."
    )


def test_scenario_fenced_code_left_alone(project: Workspace) -> None:
    fenced = DESIGN.replace("Cut the result list after sorting.", "```\n* item  \n```")
    project.change(design=fenced)
    assert fix_layout(project.root) == ()
    assert project.read(DESIGN_FILE) == fenced


def test_scenario_nothing_to_fix(project: Workspace) -> None:
    project.change()
    before = {name: project.read(f"changes/{NAME}/{name}") for name in ("proposal.md", "tasks.md")}
    assert fix_layout(project.root) == ()
    assert {name: project.read(f"changes/{NAME}/{name}") for name in before} == before


def test_scenario_accepted_change_fixed(project: Workspace) -> None:
    project.change()
    lifecycle.accept(project.root, NAME, DAY)
    project.replace(
        DESIGN_FILE, "Sorting everything costs memory.", "Sorting everything costs memory.   "
    )
    assert fix_layout(project.root) == (FixedFile(DESIGN_FILE, (Fix.TRAILING_SPACES,)),)
    assert "memory.   " not in project.read(DESIGN_FILE)
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_scenario_older_record_format(project: Workspace) -> None:
    project.change(proposal_text=proposal() + "\n\n\n")
    project.replace("config.toml", "record_format = 3", "record_format = 2")
    before = project.read(PROPOSAL_FILE)
    with pytest.raises(Refusal, match="wm update"):
        fix_layout(project.root)
    assert project.read(PROPOSAL_FILE) == before


def test_archived_changes_are_never_fixed(project: Workspace) -> None:
    folder = "changes/archive/2026-01-20-old-limit"
    project.write(f"{folder}/proposal.md", proposal(outcome="Done.") + "\n\n\n")
    project.write(f"{folder}/tasks.md", TASKS)
    before = project.read(f"{folder}/proposal.md")
    assert fix_layout(project.root) == ()
    assert project.read(f"{folder}/proposal.md") == before


def test_a_fix_that_would_change_evidence_is_refused(
    project: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    project.change(design=DESIGN + "  \n")
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    before = {path: project.read(path) for path in (DESIGN_FILE, TASKS_FILE)}

    def unticks(text: str) -> tuple[str, tuple[Fix, ...]]:
        return text.replace("- [x]", "- [ ]").rstrip(" \n") + "\n", (Fix.TRAILING_SPACES,)

    monkeypatch.setattr(fix, "standard_layout", unticks)
    with pytest.raises(Refusal, match="fault in wm"):
        fix_layout(project.root)
    assert {path: project.read(path) for path in before} == before

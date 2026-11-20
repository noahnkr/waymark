"""wm check --fix: the standard layout, and what a fix never changes."""

import datetime

import pytest

from tests.support import DESIGN, TASKS, Workspace, bold, proposal
from waymark.record.state import AcceptanceState
from waymark.record.writing.layout import Fix
from waymark.services import fix, lifecycle
from waymark.services.common import Refusal
from waymark.services.fix import FixedFile, fix_layout

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)
PROPOSAL_FILE = f"changes/{NAME}/proposal.md"
DESIGN_FILE = f"changes/{NAME}/design.md"
TASKS_FILE = f"changes/{NAME}/tasks.md"


def test_scenario_layout_fixed(project: Workspace) -> None:
    untidy = bold(proposal()).replace(
        "Search returns a capped list.", "* Search returns a capped list.  "
    )
    project.change(proposal_text=untidy, design=bold(DESIGN), tasks=bold(TASKS))
    fixed = fix_layout(project.root)
    assert fixed == (FixedFile(PROPOSAL_FILE, (Fix.LIST_MARKERS, Fix.TRAILING_SPACES)),)
    assert project.read(PROPOSAL_FILE) == untidy.replace(
        "* Search returns a capped list.  ", "- Search returns a capped list."
    )


def test_scenario_fenced_code_left_alone(project: Workspace) -> None:
    fenced = bold(DESIGN).replace(
        "Cut the result list after sorting.", "```\n* item  \n- Owner: Ada\n```"
    )
    project.change(proposal_text=bold(proposal()), design=fenced, tasks=bold(TASKS))
    assert fix_layout(project.root) == ()
    assert project.read(DESIGN_FILE) == fenced


def test_scenario_nothing_to_fix(project: Workspace) -> None:
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(TASKS))
    before = {name: project.read(f"changes/{NAME}/{name}") for name in ("proposal.md", "tasks.md")}
    assert fix_layout(project.root) == ()
    assert {name: project.read(f"changes/{NAME}/{name}") for name in before} == before


def test_scenario_accepted_change_fixed(project: Workspace) -> None:
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(TASKS))
    lifecycle.accept(project.root, NAME, DAY)
    project.replace(
        DESIGN_FILE, "Sorting everything costs memory.", "Sorting everything costs memory.   "
    )
    assert fix_layout(project.root) == (FixedFile(DESIGN_FILE, (Fix.TRAILING_SPACES,)),)
    assert "memory.   " not in project.read(DESIGN_FILE)
    assert project.change_state().acceptance is AcceptanceState.VALID


def test_scenario_record_in_another_format(project: Workspace) -> None:
    project.change(proposal_text=proposal() + "\n\n\n")
    project.replace("config.toml", "record_format = 1", "record_format = 3")
    before = project.read(PROPOSAL_FILE)
    with pytest.raises(Refusal, match="Install the wm version that wrote it") as refusal:
        fix_layout(project.root)
    assert "wm update" not in str(refusal.value)
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
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN) + "  \n", tasks=bold(TASKS))
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    before = {path: project.read(path) for path in (DESIGN_FILE, TASKS_FILE)}

    def unticks(text: str, **_: bool) -> tuple[str, tuple[Fix, ...]]:
        return text.replace("- [x]", "- [ ]").rstrip(" \n") + "\n", (Fix.TRAILING_SPACES,)

    monkeypatch.setattr(fix, "standard_layout", unticks)
    with pytest.raises(Refusal, match="fault in wm"):
        fix_layout(project.root)
    assert {path: project.read(path) for path in before} == before


def test_scenario_plain_label_made_bold(project: Workspace) -> None:
    """Requirement "Fix the layout on request": a plain label becomes bold, wording kept."""
    plain = bold(proposal(owner="Ada")).replace("- **Owner:** Ada\n", "- Owner: Ada\n")
    project.change(proposal_text=plain, design=bold(DESIGN), tasks=bold(TASKS))
    fixed = fix_layout(project.root)
    assert fixed == (FixedFile(PROPOSAL_FILE, (Fix.LABEL,)),)
    text = project.read(PROPOSAL_FILE)
    assert "\n- **Owner:** Ada\n" in text
    assert "\n- **Specs:** `search`\n" in text
    assert text == bold(proposal(owner="Ada"))


def test_scenario_glossary_entry_made_bold(project: Workspace) -> None:
    """Requirement "Fix the layout on request": charter glossary entries become bold."""
    entries = "- Record: everything in waymark/\n- **Atlas**: a separate repository\n"
    project.replace("charter.md", "- **Match:** a document that satisfies the query.\n", entries)
    before = project.read("charter.md")
    fixed = fix_layout(project.root)
    assert fixed == (FixedFile("charter.md", (Fix.LABEL,)),)
    expected = before.replace(
        entries,
        "- **Record:** everything in waymark/\n- **Atlas:** a separate repository\n",
    )
    assert project.read("charter.md") == expected


def test_only_the_charters_glossary_entries_are_made_bold(project: Workspace) -> None:
    """Lines outside the glossary, comments and fenced code in the charter keep their form."""
    project.replace(
        "charter.md",
        "## Context\n",
        "## Context\n\n- Layout: plain\n\n<!--\n- Term: in a comment\n-->\n\n"
        "```\n- Term: in a fence\n```\n",
    )
    before = project.read("charter.md")
    assert fix_layout(project.root) == ()
    assert project.read("charter.md") == before


def test_colon_outside_the_bold_and_bare_labels_are_fixed(project: Workspace) -> None:
    removed = (
        "# Search\n\nRepos: api\n\n## REMOVED Requirements\n\n"
        "### Requirement: Result limit\nReason: gone\n"
    )
    project.write(
        "specs/search.md",
        "# Search\n\n## Purpose\n\nSearch.\n\n## Requirements\n\n"
        "### Requirement: Result limit\nA search SHALL cap.\n\n#### Scenario: Cap\n"
        "- GIVEN a\n- WHEN b\n- THEN c\n",
    )
    project.write(
        "resources/stripe.md",
        "# Stripe\n\n- **Kind**: service\n- **Serves:** none\n- Status: active\n"
        "- **Verified:** 2026-11-17\n\n## What it is\n\nNone.\n",
    )
    project.change(
        proposal_text=bold(proposal()),
        deltas={"search": removed},
        design=bold(DESIGN),
        tasks=bold(TASKS),
    )
    fix_layout(project.root)
    assert "\n**Repos:** api\n" in project.read(f"changes/{NAME}/specs/search.md")
    assert "\n**Reason:** gone\n" in project.read(f"changes/{NAME}/specs/search.md")
    resource = project.read("resources/stripe.md")
    assert "\n- **Kind:** service\n" in resource
    assert "\n- **Status:** active\n" in resource


def test_the_charter_keeps_its_lines(project: Workspace) -> None:
    """The charter holds no labels: a "- Code:" line in its Context is wording."""
    project.replace("charter.md", "The search index is rebuilt nightly.", "- Code: in src/")
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(TASKS))
    assert fix_layout(project.root) == ()
    assert "\n- Code: in src/\n" in project.read("charter.md")


ORDERED = (
    "- [ ] 1.2 Rebuild the index\n"
    "  - **Build:** implementer\n"
    "  - **Criteria:**\n"
    "    - rebuilt\n"
    "    - answers\n"
    "  - **Verify:** wm check\n"
)


def test_scenario_item_lines_put_in_order(project: Workspace) -> None:
    out_of_order = (
        "- [ ] 1.2 Rebuild the index\n"
        "  - **Criteria:**\n"
        "    - rebuilt\n"
        "    - answers\n"
        "  - **Verify:** wm check\n"
        "  - **Build:** implementer\n"
    )
    tasks = "# Tasks\n\n## 1. Limit\n\n" + bold(TASKS.split("## 1. Limit\n\n")[1])
    tasks = tasks.replace("- [ ] 1.2 Document the limit", "- [ ] 1.3 Document the limit")
    tasks = tasks.replace("- [ ] 1.3", out_of_order + "- [ ] 1.3")
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=tasks)
    assert fix_layout(project.root) == (FixedFile(TASKS_FILE, (Fix.ITEM_ORDER,)),)
    assert ORDERED + "- [ ] 1.3" in project.read(TASKS_FILE)


def test_records_under_an_item_stay_after_its_lines(project: Workspace) -> None:
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(TASKS))
    lifecycle.accept(project.root, NAME, DAY)
    text = project.read(TASKS_FILE).replace(
        "  - **Verify:** read the help text\n",
        "  - **Verify:** read the help text\n  - 2026-01-15 (note) by Sam Doe: half done\n",
    )
    moved = (
        text.replace(
            "1.2 Document the limit\n  - **Build:** planner\n", "1.2 Document the limit\n"
        ).replace("  - **Criteria:** the help text names the limit\n", "")
    ).replace(
        "  - **Verify:** read the help text\n",
        "  - **Verify:** read the help text\n  - **Build:** planner\n"
        "  - **Criteria:** the help text names the limit\n",
    )
    project.write(TASKS_FILE, moved)
    fix_layout(project.root)
    item = project.read(TASKS_FILE).split("- [ ] 1.2 Document the limit\n")[1]
    assert item.startswith(
        "  - **Build:** planner\n"
        "  - **Criteria:** the help text names the limit\n"
        "  - **Verify:** read the help text\n"
        "  - 2026-01-15 (note) "
    )


def test_old_shaped_records_are_left_as_written(project: Workspace) -> None:
    """No command migrates a record: an old shape stays, and wm check reports it."""
    project.change(proposal_text=bold(proposal()), design=bold(DESIGN), tasks=bold(TASKS))
    lifecycle.accept(project.root, NAME, DAY)
    text = project.read(TASKS_FILE)
    old = text.replace("- 2026-01-15 (accepted) ", "- (accepted) 2026-01-15 ")
    assert old != text
    project.write(TASKS_FILE, old)
    assert fix_layout(project.root) == ()
    assert project.read(TASKS_FILE) == old
    codes = {p.code for p in project.record().changes[NAME].problems}
    assert "malformed-record" in codes

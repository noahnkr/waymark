"""The migration to record format 3: what humans write takes its new layout."""

from tests.support import CHARTER, Workspace, document
from waymark.record.charter import parse_charter
from waymark.record.deltas import parse_delta
from waymark.record.files import RecordFiles
from waymark.record.proposal import parse_proposal
from waymark.record.record import load_archived_change
from waymark.services.migrations import MIGRATIONS, migrate

ARCHIVED = "changes/archive/2026-01-20-old-limit"
OLD_PROPOSAL = (
    "# Old limit\n\nOwner: Ada\nReview: independent\n\n## Why\n\nSlow.\n\n## What changes\n\n"
    "Capped.\n\n## Non-goals\n\nPaging.\n\n## Impact\n\nSpecs: search.\n\n## Outcome\n\nDone.\n"
)
OLD_TASKS = (
    "# Tasks\n\n## 1. Limit\n\n- [x] 1.1 Cap it   `build: delegate`\n"
    "  - Criteria: fifty at most\n- [x] 1.2 Say so\n\n## Log\n\n"
    "- (accepted) 2026-01-15 fingerprint 0123456789abcdef items 1.1 1.2 by Ada\n"
    "- (self-review) 2026-01-16 by Ada: fine\n"
)
OLD_DELTA = (
    "# Search\n\n## Added requirements\n\n### Requirement: Result limit\n"
    "A search SHALL return at most fifty results.\n\n#### Scenario: Many\n"
    "- GIVEN many matches\n- WHEN a search runs\n- THEN fifty come back\n"
)
OLD_EXPLORATION = (
    "# Paging\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
    "## Conclusion\n\nParked: waits for a second user\n\n## Related\n"
)
OLD_GLOSSARY = CHARTER.replace(
    "- **Match**: a document that satisfies the query.",
    "Match: a document that satisfies the query.",
).replace("### apply", "### apply")


def at_format_2(workspace: Workspace) -> Workspace:
    workspace.replace("config.toml", "record_format = 3", "record_format = 2")
    return workspace


def test_scenario_format_2_record_migrated(workspace: Workspace) -> None:
    at_format_2(workspace)
    workspace.write("charter.md", OLD_GLOSSARY)
    workspace.write(f"{ARCHIVED}/proposal.md", OLD_PROPOSAL)
    workspace.write(f"{ARCHIVED}/tasks.md", OLD_TASKS)
    workspace.write(f"{ARCHIVED}/specs/search.md", OLD_DELTA)
    workspace.write("explorations/paging.md", OLD_EXPLORATION)
    done = migrate(RecordFiles(workspace.path("")))
    assert done == (f"format 2 to 3: {MIGRATIONS[1].summary}",)
    assert "record_format = 3" in workspace.read("config.toml")

    proposal = workspace.read(f"{ARCHIVED}/proposal.md")
    assert "\n- Owner: Ada\n- Review: independent\n" in proposal
    assert proposal.replace("- Owner", "Owner").replace("- Review", "Review") == OLD_PROPOSAL
    tasks = workspace.read(f"{ARCHIVED}/tasks.md")
    assert "- [x] 1.1 Cap it\n  - Criteria: fifty at most\n  - Build: delegate\n- [x] 1.2" in tasks
    assert "## ADDED Requirements\n" in workspace.read(f"{ARCHIVED}/specs/search.md")
    exploration = workspace.read("explorations/paging.md")
    assert exploration.startswith("# Paging\n\n- Status: parked\n\n## Context")
    assert "## Conclusion\n\nwaits for a second user\n" in exploration
    charter = workspace.read("charter.md")
    assert "- **Match**: a document that satisfies the query.\n" in charter
    assert "### Apply\n" in charter

    record = workspace.record()
    assert record.problems == ()
    change = load_archived_change(record, record.archived_changes[0])
    assert change.problems == ()
    assert change.tasks is not None
    assert change.tasks.items[0].delegate


def test_a_linked_conclusion_becomes_led_to(workspace: Workspace) -> None:
    at_format_2(workspace)
    workspace.change()
    workspace.write(
        "explorations/paging.md",
        OLD_EXPLORATION.replace(
            "Parked: waits for a second user", "See [add-limit](../changes/add-limit/proposal.md)."
        ),
    )
    migrate(RecordFiles(workspace.path("")))
    exploration = workspace.read("explorations/paging.md")
    assert "- Status: led-to [add-limit](../changes/add-limit/proposal.md)\n" in exploration


def test_wording_is_never_changed(workspace: Workspace) -> None:
    at_format_2(workspace)
    workspace.write("explorations/paging.md", OLD_EXPLORATION.replace("Parked: waits", "We wait"))
    migrate(RecordFiles(workspace.path("")))
    text = workspace.read("explorations/paging.md")
    assert "- Status: open\n" in text
    assert "We wait for a second user" in text


def test_scenario_old_fact_line() -> None:
    parsed = parse_proposal(document(OLD_PROPOSAL, "changes/old/proposal.md"))
    assert {problem.code for problem in parsed.problems} == {"old-layout"}
    assert all("wm update" in problem.message for problem in parsed.problems)


def test_scenario_old_glossary_line() -> None:
    parsed = parse_charter(document(OLD_GLOSSARY, "charter.md"))
    [problem] = parsed.problems
    assert problem.code == "glossary-format"
    assert "- **<term>**: <meaning>" in problem.message


def test_old_delta_headings_are_an_old_layout() -> None:
    parsed = parse_delta("search", document(OLD_DELTA, "changes/x/specs/search.md"))
    assert [problem.code for problem in parsed.problems] == ["old-layout"]
    assert [item.name for item in parsed.added] == ["Result limit"]

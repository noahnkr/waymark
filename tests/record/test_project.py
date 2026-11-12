"""Finding the project and loading the record from its files."""

import datetime
from pathlib import Path

import pytest

from tests.support import CONFIG, Workspace, delta, proposal, requirement, spec
from waymark.record.problems import Problem
from waymark.record.project import ProjectNotFoundError, find_project
from waymark.record.record import ArchiveEntry, load_archived_change, load_record, spec_history
from waymark.record.terms import Layout, ReviewLevel


def codes(problems: tuple[Problem, ...]) -> list[tuple[str, str]]:
    return [(problem.path, problem.code) for problem in problems]


def test_project_is_found_from_any_folder_inside_it(workspace: Workspace) -> None:
    nested = workspace.root / "src" / "deep"
    nested.mkdir(parents=True)
    project = find_project(nested)
    assert project.root == workspace.root.resolve()
    assert project.record_root == workspace.root.resolve() / "waymark"
    assert find_project(workspace.path("changes")).root == project.root


def test_project_not_found_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError) as error:
        find_project(tmp_path)
    assert "waymark/config.toml" in str(error.value)
    assert "initialize" in str(error.value)


def test_atlas_is_found_the_same_way_and_known_from_its_settings(atlas: Workspace) -> None:
    record = load_record(find_project(atlas.root))
    assert record.problems == ()
    assert record.layout is Layout.ATLAS
    assert record.config is not None
    assert record.config.repo_names == {"api", "web"}


def test_record_in_a_repo_has_the_repo_layout(workspace: Workspace) -> None:
    record = workspace.record()
    assert record.problems == ()
    assert record.layout is Layout.REPO
    assert record.default_review is ReviewLevel.SELF
    assert record.charter is not None


def test_record_loads_every_kind_of_artifact(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    workspace.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    workspace.write(
        "milestones/faster-search/goal.md",
        "# G\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n",
    )
    workspace.write("milestones/faster-search/roadmap.md", "# Roadmap\n\n- Cache hot queries\n")
    workspace.write(
        "explorations/paging.md",
        "# P\n\n## Context\n\n## Questions\n\n## Approaches\n\n## Conclusion\n\n## Related\n",
    )
    record = workspace.record()
    assert record.problems == ()
    assert list(record.specs) == ["search"]
    assert list(record.changes) == ["add-order"]
    assert list(record.milestones) == ["faster-search"]
    assert list(record.explorations) == ["paging"]
    change = record.changes["add-order"]
    assert change.proposal is not None
    assert change.design is not None
    assert change.tasks is not None
    assert list(change.deltas) == ["search"]


def test_change_is_active_or_archived_by_where_its_folder_sits(workspace: Workspace) -> None:
    workspace.change("add-order")
    workspace.write("changes/archive/2026-01-20-add-limit/proposal.md", proposal(outcome="Done."))
    workspace.write("changes/archive/2025-11-02-add-limit/proposal.md", proposal())
    record = workspace.record()
    assert list(record.changes) == ["add-order"]
    assert record.archived_changes == (
        ArchiveEntry(
            datetime.date(2025, 11, 2), "add-limit", "changes/archive/2025-11-02-add-limit"
        ),
        ArchiveEntry(
            datetime.date(2026, 1, 20), "add-limit", "changes/archive/2026-01-20-add-limit"
        ),
    )
    archived = load_archived_change(record, record.archived_changes[1])
    assert archived.archived_on == datetime.date(2026, 1, 20)
    assert archived.proposal is not None
    assert archived.proposal.outcome == "Done."


def test_record_is_read_fresh_on_every_load(workspace: Workspace) -> None:
    assert list(workspace.record().changes) == []
    workspace.change()
    assert list(workspace.record().changes) == ["add-limit"]


def test_missing_charter_is_a_problem(workspace: Workspace) -> None:
    workspace.path("charter.md").unlink()
    assert codes(workspace.record().problems) == [("charter.md", "missing-file")]


def test_broken_settings_are_a_problem_and_the_record_still_loads(workspace: Workspace) -> None:
    workspace.write("config.toml", CONFIG + "tint = 1\n")
    workspace.change()
    record = workspace.record()
    assert record.config is None
    assert codes(record.problems) == [("config.toml", "unknown-setting")]
    assert list(record.changes) == ["add-limit"]


def test_names_that_break_the_naming_rule_are_problems(workspace: Workspace) -> None:
    workspace.write("specs/Search_V2.md", spec())
    workspace.write("changes/add-limit-2/proposal.md", proposal())
    workspace.write("changes/archive/add-limit/proposal.md", proposal())
    workspace.write("explorations/Paging.md", "# P\n")
    record = workspace.record()
    assert codes(record.problems) == [
        ("changes/add-limit-2", "invalid-name"),
        ("changes/archive/add-limit", "invalid-name"),
        ("explorations/Paging.md", "invalid-name"),
        ("specs/Search_V2.md", "invalid-name"),
    ]
    assert record.specs == {}
    assert record.changes == {}


def test_files_that_do_not_belong_are_problems(workspace: Workspace) -> None:
    workspace.change()
    workspace.write("changes/add-limit/notes.md", "scratch\n")
    workspace.write("changes/add-limit/specs/search.txt", "x\n")
    workspace.write("changes/stray.md", "x\n")
    workspace.write("specs/drafts/search.md", spec())
    assert codes(workspace.record().problems) == [
        ("changes/add-limit/notes.md", "unexpected-file"),
        ("changes/add-limit/specs/search.txt", "unexpected-file"),
        ("changes/stray.md", "unexpected-file"),
        ("specs/drafts", "unexpected-file"),
    ]


def test_hidden_files_are_ignored(workspace: Workspace) -> None:
    workspace.write("specs/.gitkeep", "")
    workspace.write("changes/.DS_Store", "x")
    assert workspace.record().problems == ()


def test_file_that_is_not_utf8_is_a_problem(workspace: Workspace) -> None:
    workspace.path("specs").mkdir()
    workspace.path("specs/search.md").write_bytes(b"# Search \xe9\n")
    record = workspace.record()
    assert codes(record.problems) == [("specs/search.md", "not-utf8")]
    assert record.specs == {}


def test_milestone_needs_a_goal_and_a_roadmap(workspace: Workspace) -> None:
    workspace.write("milestones/faster-search/roadmap.md", "# Roadmap\n")
    assert codes(workspace.record().problems) == [
        ("milestones/faster-search/goal.md", "missing-file")
    ]


def test_problems_are_reported_with_record_relative_paths_and_lines(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec("### Requirement: Result limit\nSearch SHALL stop.\n"))
    (problem,) = workspace.record().problems
    assert (problem.path, problem.line, problem.code) == (
        "specs/search.md",
        9,
        "requirement-without-scenario",
    )


def test_spec_history_lists_archived_changes_that_touched_the_spec(workspace: Workspace) -> None:
    for date, name, outcome in (
        ("2026-01-20", "add-limit", "Capped at fifty."),
        ("2026-02-11", "fix-order", None),
        ("2026-03-01", "add-paging", "Paging added."),
    ):
        folder = f"changes/archive/{date}-{name}"
        workspace.write(f"{folder}/proposal.md", proposal(outcome=outcome))
        domain = "export" if name == "fix-order" else "search"
        workspace.write(f"{folder}/specs/{domain}.md", delta(added=(requirement(),)))
    history = spec_history(workspace.record(), "search")
    assert [(entry.date.isoformat(), entry.change, entry.outcome) for entry in history] == [
        ("2026-01-20", "add-limit", "Capped at fifty."),
        ("2026-03-01", "add-paging", "Paging added."),
    ]


def test_archived_changes_are_not_parsed_until_asked_for(workspace: Workspace) -> None:
    workspace.write("changes/archive/2026-01-20-add-limit/proposal.md", "not a proposal at all\n")
    record = workspace.record()
    assert record.problems == ()
    archived = load_archived_change(record, record.archived_changes[0])
    assert archived.problems != ()

"""Paths, encodings and line endings behave the same on every platform."""

from tests.support import Workspace, delta, requirement, spec
from waymark.record.deltas import merge_delta
from waymark.record.problems import Problem


def as_windows(workspace: Workspace) -> None:
    for path in sorted(workspace.path("").rglob("*.md")):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))


def test_record_reads_the_same_with_windows_line_endings(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    workspace.change("fix-limit", deltas={"search": delta(modified=(requirement(),))})
    workspace.accept("fix-limit")
    before = workspace.state()
    problems = workspace.record().problems
    as_windows(workspace)
    assert b"\r\n" in workspace.path("specs/search.md").read_bytes()
    assert workspace.state() == before
    assert workspace.record().problems == problems == ()


def test_record_files_are_read_as_utf8(workspace: Workspace) -> None:
    statement = "A search SHALL match “café”, naïve and 検索 alike."
    workspace.write("specs/search.md", spec(requirement(statement=statement)))
    record = workspace.record()
    assert record.problems == ()
    assert record.specs["search"].requirements[0].statement == statement


def test_merge_keeps_non_ascii_text_and_line_endings_byte_for_byte(workspace: Workspace) -> None:
    kept = requirement("Accents", "A search SHALL match “café” and 検索.")
    workspace.write("specs/search.md", spec(requirement(), kept).replace("\n", "\r\n"))
    workspace.change(
        "fix-limit", deltas={"search": delta(modified=(requirement(scenario="Edge"),))}
    )
    record = workspace.record()
    merged = merge_delta(record.specs["search"], record.changes["fix-limit"].deltas["search"])
    assert merged.text is not None
    before = workspace.path("specs/search.md").read_bytes()
    after = merged.text.encode("utf-8")
    tail = b"### Requirement: Accents"
    assert after[after.index(tail) :] == before[before.index(tail) :]
    assert b"\n" not in after.replace(b"\r\n", b"")


def test_problem_paths_use_forward_slashes_on_every_platform(workspace: Workspace) -> None:
    workspace.change()
    workspace.write("changes/add-limit/specs/search.md", "# Search\n")
    (problem,) = workspace.record().problems
    assert problem == Problem(
        "changes/add-limit/specs/search.md", 1, "empty-delta", problem.message
    )
    assert "\\" not in problem.path


def test_project_in_a_folder_with_spaces_and_non_ascii_letters(workspace: Workspace) -> None:
    odd = Workspace(workspace.root.parent / "my prøject ü")
    odd.change()
    assert odd.record().problems == ()
    assert list(odd.state().changes) == ["add-limit"]

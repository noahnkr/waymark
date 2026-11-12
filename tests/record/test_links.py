"""Links between record files."""

from tests.support import Workspace, spec
from waymark.record.links import local_path, resolve
from waymark.record.record import link_problems


def link_codes(workspace: Workspace) -> list[tuple[str, int, str]]:
    return [(p.path, p.line, p.code) for p in link_problems(workspace.record())]


def explore(workspace: Workspace, body: str) -> None:
    workspace.write(
        "explorations/paging.md",
        f"# Paging\n\n## Context\n\n{body}\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\n## Related\n",
    )


def test_relative_link_to_an_existing_file_is_fine(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    explore(workspace, "See [search](../specs/search.md#requirements) and [specs](../specs/).")
    assert link_codes(workspace) == []


def test_link_to_a_missing_file_is_broken(workspace: Workspace) -> None:
    explore(workspace, "See [search](../specs/search.md).")
    assert link_codes(workspace) == [("explorations/paging.md", 5, "broken-link")]


def test_link_names_are_matched_exactly_on_every_platform(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    explore(workspace, "See [search](../specs/Search.md).")
    assert link_codes(workspace) == [("explorations/paging.md", 5, "broken-link")]


def test_web_links_and_anchors_are_not_checked(workspace: Workspace) -> None:
    explore(
        workspace, "[site](https://example.com/x.md) [mail](mailto:a@example.com) [top](#context)"
    )
    assert link_codes(workspace) == []


def test_absolute_link_is_a_problem(workspace: Workspace) -> None:
    explore(workspace, "[a](/etc/hosts) and [b](C:/notes/plan.md)")
    assert [code for _, _, code in link_codes(workspace)] == ["absolute-link", "absolute-link"]


def test_link_with_backslashes_is_a_problem(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    explore(workspace, "[search](..\\specs\\search.md)")
    assert [code for _, _, code in link_codes(workspace)] == ["broken-link"]


def test_link_may_leave_the_record_for_a_file_in_the_repo(workspace: Workspace) -> None:
    (workspace.root / "README.md").write_text("hello\n", encoding="utf-8")
    explore(workspace, "[readme](../../README.md) and [gone](../../MISSING.md)")
    assert [code for _, _, code in link_codes(workspace)] == ["broken-link"]


def test_link_with_escaped_spaces_is_resolved(workspace: Workspace) -> None:
    (workspace.root / "user guide.md").write_text("hello\n", encoding="utf-8")
    explore(workspace, "[guide](../../user%20guide.md)")
    assert link_codes(workspace) == []


def test_links_in_every_active_artifact_are_checked(workspace: Workspace) -> None:
    workspace.change()
    workspace.replace("changes/add-limit/design.md", "after sorting.", "after [sorting](sort.md).")
    workspace.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    assert link_codes(workspace) == [
        ("changes/add-limit/design.md", 9, "broken-link"),
        ("charter.md", 25, "broken-link"),
    ]


def test_resolve_gives_a_path_relative_to_the_record_root() -> None:
    assert resolve("changes/add-limit/proposal.md", "specs/search.md") == (
        "changes/add-limit/specs/search.md"
    )
    assert (
        resolve("milestones/faster/roadmap.md", "../../changes/add-limit/") == "changes/add-limit"
    )
    assert resolve("charter.md", "../README.md") == "../README.md"
    assert resolve("charter.md", "https://example.com") is None


def test_local_path_drops_anchors_and_queries() -> None:
    assert local_path("a/b.md#part") == "a/b.md"
    assert local_path("a/b.md?x=1") == "a/b.md"
    assert local_path("#part") is None

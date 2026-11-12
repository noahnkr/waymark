"""The health check: errors that fail it, and warnings that don't."""

import datetime
import os
import subprocess

from tests.support import Workspace, delta, requirement, spec
from waymark.services import lifecycle
from waymark.services.check import Finding, Severity, check, has_errors

NOW = datetime.datetime(2026, 3, 1, 12, tzinfo=datetime.UTC)
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def findings(project: Workspace) -> list[tuple[str, str, str]]:
    return [(f.severity.value, f.path, f.code) for f in check(project.root, NOW)]


def commit_all(project: Workspace, date: str) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_EMAIL": "sam@example.com",
        "GIT_COMMITTER_EMAIL": "sam@example.com",
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    for arguments in (["add", "--all"], ["commit", "--quiet", "--message", "chore: save"]):
        subprocess.run(
            ["git", "-C", str(project.root), *arguments],
            check=True,
            capture_output=True,
            env=environment,
        )


def test_healthy_record_has_no_findings(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    project.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    result = check(project.root, NOW)
    assert result == ()
    assert not has_errors(result)


def test_format_problems_are_errors(project: Workspace) -> None:
    project.write("specs/search.md", spec("### Requirement: Result limit\nSearch SHALL stop.\n"))
    result = check(project.root, NOW)
    assert has_errors(result)
    (finding,) = result
    assert finding == Finding(
        Severity.ERROR, "specs/search.md", 9, "requirement-without-scenario", finding.message
    )


def test_broken_links_are_errors(project: Workspace) -> None:
    project.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    assert findings(project) == [("error", "charter.md", "broken-link")]


def test_malformed_evidence_is_an_error(project: Workspace) -> None:
    project.change(tasks=HEAD + "- [x] 1.1 Cap it\n  - (review) approved by me\n")
    assert findings(project) == [("error", "changes/add-limit/tasks.md", "malformed-evidence")]


def test_delta_that_does_not_match_its_spec_is_an_error(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement("Result cap")))
    project.change(deltas={"search": delta(modified=(CHANGED,))})
    assert findings(project) == [("error", "changes/add-limit", "conflict")]


def test_overlapping_changes_are_a_warning(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    project.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    project.change("drop-limit", deltas={"search": delta(removed=(("Result limit", "Unused."),))})
    result = check(project.root, NOW)
    assert [(f.severity, f.code) for f in result] == [(Severity.WARNING, "overlap")]
    assert "drop-limit and fix-limit" in result[0].message
    assert not has_errors(result)


def test_change_applied_but_not_archived_is_a_warning(project: Workspace) -> None:
    project.change(tasks=HEAD + "- [ ] 1.1 Rename it   `review: none`\n")
    lifecycle.accept(project.root, "add-limit", DAY)
    assert findings(project) == []
    lifecycle.tick(project.root, "add-limit", "1.1")
    assert findings(project) == [("warning", "changes/add-limit", "not-archived")]


def test_unreadable_exploration_conclusion_is_an_error(project: Workspace) -> None:
    project.write(
        "explorations/paging.md",
        "# P\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\nWe should think more.\n\n## Related\n",
    )
    assert findings(project) == [("error", "explorations/paging.md", "conclusion-unreadable")]


def test_change_untouched_for_a_while_is_a_warning(project: Workspace) -> None:
    order = delta(title="Order", added=(requirement("Result order"),), purpose="How order works.")
    project.change("add-order", deltas={"order": order})
    commit_all(project, "2026-01-01T09:00:00+00:00")
    project.change("add-limit")
    commit_all(project, "2026-02-20T09:00:00+00:00")
    result = check(project.root, NOW)
    assert [(f.severity, f.path, f.code) for f in result] == [
        (Severity.WARNING, "changes/add-order", "stale")
    ]
    assert "59 days" in result[0].message


def test_change_not_committed_yet_is_not_stale(project: Workspace) -> None:
    project.change()
    assert findings(project) == []


def test_findings_come_in_a_stable_order_with_errors_first(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    project.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    project.change("drop-limit", deltas={"search": delta(removed=(("Result limit", "Unused."),))})
    project.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    first = check(project.root, NOW)
    assert first == check(project.root, NOW)
    assert [f.severity for f in first] == [Severity.ERROR, Severity.WARNING]

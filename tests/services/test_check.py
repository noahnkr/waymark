"""The health check: errors that fail it, and warnings that don't."""

import datetime
import os
import subprocess

from tests.support import IMPACT, Workspace, delta, proposal, requirement, spec
from waymark.services import lifecycle
from waymark.services.check import Finding, Severity, check, has_errors

NOW = datetime.datetime(2026, 3, 1, 12, tzinfo=datetime.UTC)
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def reviewed_at(level: str) -> str:
    return proposal().replace("Owner: Sam Doe\n", f"Owner: Sam Doe\n- Review: {level}\n")


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


def old_layouts(project: Workspace) -> list[tuple[str, int]]:
    result = check(project.root, NOW)
    found = [(f.path, f.line) for f in result if f.code == "old-layout"]
    assert all("wm update" in f.message for f in result if f.code == "old-layout")
    assert all(f.severity is Severity.ERROR for f in result if f.code == "old-layout")
    return found


def test_scenario_old_fact_line(project: Workspace) -> None:
    project.change()
    project.replace("changes/add-limit/proposal.md", "- Owner: Sam Doe\n", "Owner: Sam Doe\n")
    assert old_layouts(project) == [("changes/add-limit/proposal.md", 3)]


def test_scenario_old_glossary_line(project: Workspace) -> None:
    project.replace(
        "charter.md",
        "- **Match**: a document that satisfies the query.\n",
        "Record: everything in waymark/\n",
    )
    [finding] = [f for f in check(project.root, NOW) if f.path == "charter.md"]
    assert finding.code == "old-layout"
    assert "wm update" in finding.message
    assert "- **<term>**: <meaning>" in finding.message


def test_old_delta_headings_are_old_layouts(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    text = delta(added=(requirement("Result order"),)).replace(
        "## ADDED Requirements", "## Added requirements"
    )
    project.change("add-order", deltas={"search": text})
    assert [path for path, _ in old_layouts(project)] == ["changes/add-order/specs/search.md"]


def test_scenario_impact_matches_the_deltas(project: Workspace) -> None:
    project.change(proposal_text=proposal(impact=IMPACT.replace("`search`", "`search` (modified)")))
    assert [f for f in check(project.root, NOW) if f.code.startswith("impact")] == []


def test_scenario_delta_not_named_in_the_impact(project: Workspace) -> None:
    ranking = delta(title="Ranking", added=(requirement("Score"),), purpose="How ranks work.")
    project.change(deltas={"search": delta(added=(requirement(),)), "ranking": ranking})
    project.write("specs/search.md", spec())
    [finding] = [f for f in check(project.root, NOW) if f.code.startswith("impact")]
    assert (finding.severity, finding.path, finding.code) == (
        Severity.ERROR,
        "changes/add-limit/proposal.md",
        "impact-mismatch",
    )
    assert "`ranking`" in finding.message


def test_impact_needs_its_three_lines(project: Workspace) -> None:
    project.change(proposal_text=proposal(impact="- Specs: `search`"))
    [finding] = [f for f in check(project.root, NOW) if f.code.startswith("impact")]
    assert finding.code == "impact-format"
    assert '"- User-visible:", "- Code:"' in finding.message


def test_spec_named_without_a_delta_points_at_the_specs_step(project: Workspace) -> None:
    project.change(proposal_text=proposal(impact=IMPACT.replace("`search`", "`search`, `ranking`")))
    [finding] = [f for f in check(project.root, NOW) if f.code.startswith("impact")]
    assert (finding.path, finding.code) == ("changes/add-limit/specs", "impact-mismatch")
    assert project.change_state().next_step.kind.value == "specs"


def test_broken_links_are_errors(project: Workspace) -> None:
    project.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    assert findings(project) == [("error", "charter.md", "broken-link")]


def test_malformed_evidence_is_an_error(project: Workspace) -> None:
    project.change(tasks=HEAD + "- [x] 1.1 Cap it\n  - (review) approved by me\n")
    assert findings(project) == [("error", "changes/add-limit/tasks.md", "malformed-record")]


def test_unknown_build_tag_and_repeated_tag_are_errors(project: Workspace) -> None:
    project.change(
        tasks=HEAD
        + "- [ ] 1.1 Cap it\n  - Build: someone\n"
        + "- [ ] 1.2 Page it   `build: delegate`\n"
    )
    assert findings(project) == [
        ("error", "changes/add-limit/tasks.md", "unknown-build-tag"),
        ("error", "changes/add-limit/tasks.md", "old-layout"),
    ]


def test_delta_that_does_not_match_its_spec_is_an_error(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement("Result cap")))
    project.change(
        proposal_text=reviewed_at("independent"), deltas={"search": delta(modified=(CHANGED,))}
    )
    assert findings(project) == [("error", "changes/add-limit", "conflict")]


def test_overlapping_changes_are_a_warning(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    independent = reviewed_at("independent")
    project.change(
        "fix-limit", proposal_text=independent, deltas={"search": delta(modified=(CHANGED,))}
    )
    project.change(
        "drop-limit",
        proposal_text=independent,
        deltas={"search": delta(removed=(("Result limit", "Unused."),))},
    )
    result = check(project.root, NOW)
    assert [(f.severity, f.code) for f in result] == [(Severity.WARNING, "overlap")]
    assert "drop-limit and fix-limit" in result[0].message
    assert not has_errors(result)


def test_change_applied_but_not_archived_is_a_warning(project: Workspace) -> None:
    project.change(proposal_text=reviewed_at("none"), tasks=HEAD + "- [ ] 1.1 Rename it\n")
    lifecycle.accept(project.root, "add-limit", DAY)
    assert findings(project) == []
    lifecycle.tick(project.root, "add-limit", "1.1")
    assert findings(project) == [("warning", "changes/add-limit", "not-archived")]


def test_exploration_without_a_status_line_is_an_old_layout(project: Workspace) -> None:
    project.write(
        "explorations/paging.md",
        "# P\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\nWe should think more.\n\n## Related\n",
    )
    assert findings(project) == [("error", "explorations/paging.md", "old-layout")]


def test_change_untouched_for_a_while_is_a_warning(project: Workspace) -> None:
    order = delta(title="Order", added=(requirement("Result order"),), purpose="How order works.")
    impact = IMPACT.replace("`search`", "`order`")
    project.change("add-order", proposal_text=proposal(impact=impact), deltas={"order": order})
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
    independent = reviewed_at("independent")
    project.change(
        "fix-limit", proposal_text=independent, deltas={"search": delta(modified=(CHANGED,))}
    )
    project.change(
        "drop-limit",
        proposal_text=independent,
        deltas={"search": delta(removed=(("Result limit", "Unused."),))},
    )
    project.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    first = check(project.root, NOW)
    assert first == check(project.root, NOW)
    assert [f.severity for f in first] == [Severity.ERROR, Severity.WARNING]


def test_risky_change_at_self(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    project.change("fix-limit", deltas={"search": delta(modified=(CHANGED,))})
    result = check(project.root, NOW)
    assert [(f.severity, f.path, f.code) for f in result] == [
        (Severity.WARNING, "changes/fix-limit/proposal.md", "review-level")
    ]
    assert "should be reviewed independently" in result[0].message
    project.change(
        "fix-limit",
        proposal_text=reviewed_at("independent"),
        deltas={"search": delta(modified=(CHANGED,))},
    )
    assert findings(project) == []


def test_not_archived_warning_says_to_archive_before_the_pull_request(project: Workspace) -> None:
    project.change(proposal_text=reviewed_at("none"), tasks=HEAD + "- [ ] 1.1 Rename it\n")
    lifecycle.accept(project.root, "add-limit", DAY)
    lifecycle.tick(project.root, "add-limit", "1.1")
    (finding,) = check(project.root, NOW)
    assert finding.code == "not-archived"
    assert "on its branch" in finding.message
    assert "before its pull request" in finding.message
    assert "merged" not in finding.message


def test_nothing_recorded(project: Workspace) -> None:
    source = project.root / "src" / "search.py"
    source.parent.mkdir(parents=True)
    source.write_text("LIMIT = 50  # the most results a search returns\n", encoding="utf-8")
    commit_all(project, "2026-01-15T12:00:00")
    before = snapshot(project)
    source.write_text("LIMIT = 50  # the most results a search returns.\n", encoding="utf-8")
    commit_all(project, "2026-01-16T12:00:00")
    assert snapshot(project) == before
    assert check(project.root, NOW) == ()
    assert status_changes(project) == []


def snapshot(project: Workspace) -> dict[str, bytes]:
    root = project.path("")
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def status_changes(project: Workspace) -> list[object]:
    from waymark.views import payloads  # noqa: PLC0415 - only this test needs it

    return list(payloads.status(project.record())["changes"])

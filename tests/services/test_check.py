"""The health check: errors that fail it, and warnings that don't."""

import datetime
import os
import subprocess

import pytest

from tests.support import (
    DESIGN,
    IMPACT,
    NO_SPECS,
    TASKS,
    Workspace,
    delta,
    milestone,
    proposal,
    requirement,
    spec,
)
from waymark.services import lifecycle
from waymark.services.check import Finding, Severity, check, has_errors
from waymark.services.pr import describe
from waymark.views import payloads

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


def test_scenario_fact_without_a_bullet(project: Workspace) -> None:
    project.change()
    project.replace("changes/add-limit/proposal.md", "- Owner: Sam Doe\n", "Owner: Sam Doe\n")
    result = check(project.root, NOW)
    found = [(f.severity, f.path, f.code) for f in result if f.path.endswith("proposal.md")]
    assert found == [(Severity.ERROR, "changes/add-limit/proposal.md", "missing-owner")]
    assert not any("wm update" in f.message for f in result)


def test_scenario_old_glossary_line(project: Workspace) -> None:
    project.replace(
        "charter.md",
        "- **Match**: a document that satisfies the query.\n",
        "Record: everything in waymark/\n",
    )
    [finding] = [f for f in check(project.root, NOW) if f.path == "charter.md"]
    assert finding.code == "glossary-format"
    assert "wm update" not in finding.message
    assert "- **<term>**: <meaning>" in finding.message


def test_scenario_heading_in_another_case(project: Workspace) -> None:
    project.write("specs/search.md", spec())
    text = delta(added=(requirement("Result order"),)).replace(
        "## ADDED Requirements", "## Added Requirements"
    )
    project.change("add-order", deltas={"search": text})
    [finding] = [f for f in check(project.root, NOW) if f.code == "layout"]
    assert (finding.severity, finding.path) == (Severity.ERROR, "changes/add-order/specs/search.md")
    assert "## ADDED Requirements" in finding.message
    assert "wm update" not in finding.message


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


@pytest.mark.parametrize("value", ["", " search (new)"])
def test_only_specs_none_skips_the_specs_step(project: Workspace, value: str) -> None:
    """Requirement "Structured impact": an empty or unrecognized Specs line is reported."""
    impact = NO_SPECS.replace("- Specs: none", f"- Specs:{value}")
    project.change(proposal_text=proposal(impact=impact), deltas={})
    [finding] = [f for f in check(project.root, NOW) if f.code.startswith("impact")]
    assert (finding.path, finding.code) == ("changes/add-limit/proposal.md", "impact-format")
    assert "in backticks" in finding.message
    assert project.change_state().next_step.kind.value == "propose"
    project.replace("changes/add-limit/proposal.md", f"- Specs:{value}\n", "- Specs: none\n")
    assert [f for f in check(project.root, NOW) if f.code.startswith("impact")] == []


def test_spec_named_without_a_delta_points_at_the_specs_step(project: Workspace) -> None:
    project.change(proposal_text=proposal(impact=IMPACT.replace("`search`", "`search`, `ranking`")))
    [finding] = [f for f in check(project.root, NOW) if f.code.startswith("impact")]
    assert (finding.path, finding.code) == ("changes/add-limit/specs", "impact-mismatch")
    assert project.change_state().next_step.kind.value == "specs"


OLD_DESIGN = (
    DESIGN.replace("- Status: decided\n", "")
    .replace("- Decided by: planner\n", "")
    .replace("## Open questions\n\nNone.\n\n", "")
)


def test_scenario_archived_change_in_an_older_layout(project: Workspace) -> None:
    """Requirement "New work only": archived changes are read as they were written."""
    folder = "changes/archive/2026-01-20-add-limit"
    project.write(f"{folder}/proposal.md", proposal(impact="Specs: search.", outcome="Done."))
    project.write(f"{folder}/specs/search.md", delta(added=(requirement(),), purpose="Search."))
    project.write(f"{folder}/design.md", OLD_DESIGN)
    project.write(f"{folder}/tasks.md", TASKS.replace("- [ ]", "- [x]"))
    assert "- Status:" not in OLD_DESIGN
    assert "Open questions" not in OLD_DESIGN
    assert check(project.root, NOW) == ()
    record = project.record()
    shown = payloads.show(record, "add-limit")
    assert shown["name"] == "add-limit"
    body = describe(record, "add-limit")["body"]
    assert "## Outcome\n\nDone." in body
    for name in ("proposal.md", "specs/search.md", "design.md", "tasks.md"):
        project.write(f"changes/add-order/{name}", project.read(f"{folder}/{name}"))
    active = {f.code for f in check(project.root, NOW) if f.path.startswith("changes/add-order")}
    assert {"impact-format", "decision-format", "missing-section"} <= active


def test_broken_links_are_errors(project: Workspace) -> None:
    project.replace("charter.md", "rebuilt nightly.", "rebuilt [nightly](jobs.md).")
    assert findings(project) == [("error", "charter.md", "broken-link")]


def test_malformed_evidence_is_an_error(project: Workspace) -> None:
    project.change(
        tasks=HEAD
        + "- [x] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n  - (review) approved by me\n"
    )
    assert findings(project) == [("error", "changes/add-limit/tasks.md", "malformed-record")]


def test_unknown_build_tag_is_an_error(project: Workspace) -> None:
    project.change(
        tasks=HEAD
        + "- [ ] 1.1 Cap it\n  - Criteria: done\n  - Verify: a test\n  - Build: someone\n"
    )
    assert findings(project) == [("error", "changes/add-limit/tasks.md", "unknown-build-tag")]


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
    project.change(
        proposal_text=reviewed_at("none"),
        tasks=HEAD + "- [ ] 1.1 Rename it\n  - Criteria: done\n  - Verify: a test\n",
    )
    lifecycle.accept(project.root, "add-limit", DAY)
    assert findings(project) == []
    lifecycle.tick(project.root, "add-limit", "1.1")
    assert findings(project) == [("warning", "changes/add-limit", "not-archived")]


def test_exploration_without_a_status_line_is_missing_its_status(project: Workspace) -> None:
    project.write(
        "explorations/paging.md",
        "# P\n\n## Context\n\n## Questions\n\n## Approaches\n\n"
        "## Conclusion\n\nWe should think more.\n\n## Related\n",
    )
    assert findings(project) == [("error", "explorations/paging.md", "missing-status")]


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
    project.change(
        proposal_text=reviewed_at("none"),
        tasks=HEAD + "- [ ] 1.1 Rename it\n  - Criteria: done\n  - Verify: a test\n",
    )
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


LINKED = "- [add-limit](../../changes/add-limit/proposal.md): cap the results\n"


def milestone_named(milestone_name: str) -> str:
    return proposal().replace(
        "- Owner: Sam Doe\n", f"- Owner: Sam Doe\n- Milestone: {milestone_name}\n"
    )


def milestone_findings(project: Workspace) -> list[tuple[str, str, int, str]]:
    return [
        (f.severity.value, f.code, f.line, f.message)
        for f in check(project.root, NOW)
        if "milestone" in f.code
    ]


def test_scenario_proposal_and_roadmap_agree(project: Workspace) -> None:
    project.change(proposal_text=milestone_named("faster-search"))
    project.write("milestones/faster-search/milestone.md", milestone(LINKED))
    assert milestone_findings(project) == []


def test_scenario_roadmap_does_not_link_the_change(project: Workspace) -> None:
    project.change(proposal_text=milestone_named("faster-search"))
    project.write("milestones/faster-search/milestone.md", milestone("- add-limit: planned\n"))
    [(severity, code, line, message)] = milestone_findings(project)
    assert (severity, code, line) == ("error", "milestone-unlinked", 4)
    assert '"faster-search"' in message
    assert 'doesn\'t link "add-limit"' in message


def test_scenario_linked_change_names_no_milestone(project: Workspace) -> None:
    project.change()
    project.write("milestones/faster-search/milestone.md", milestone(LINKED))
    [(severity, code, _, message)] = milestone_findings(project)
    assert (severity, code) == ("error", "milestone-missing")
    assert '"- Milestone: faster-search"' in message


def test_scenario_unknown_milestone(project: Workspace) -> None:
    project.change(proposal_text=milestone_named("no-such-milestone"))
    [(severity, code, _, message)] = milestone_findings(project)
    assert (severity, code) == ("error", "unknown-milestone")
    assert '"no-such-milestone"' in message
    assert "doesn't exist" in message


def test_a_change_named_for_one_milestone_and_linked_from_another(project: Workspace) -> None:
    project.change(proposal_text=milestone_named("faster-search"))
    project.write("milestones/faster-search/milestone.md", milestone())
    project.write("milestones/better-ranking/milestone.md", milestone(LINKED))
    [(_, code, _, message)] = milestone_findings(project)
    assert code == "milestone-other"
    assert '"better-ranking"' in message


def test_a_change_on_two_roadmaps(project: Workspace) -> None:
    project.change(proposal_text=milestone_named("faster-search"))
    project.write("milestones/faster-search/milestone.md", milestone(LINKED))
    project.write("milestones/better-ranking/milestone.md", milestone(LINKED))
    [(severity, code, _, message)] = milestone_findings(project)
    assert (severity, code) == ("error", "milestone-twice")
    assert '"better-ranking", "faster-search"' in message


def test_archived_changes_are_not_checked_against_roadmaps(project: Workspace) -> None:
    project.change(
        proposal_text=milestone_named("no-such-milestone"),
        tasks="# Tasks\n\n## 1. Limit\n\n- [ ] 1.1 Cap it\n  - Verify: a test\n  - Criteria: ok\n",
    )
    lifecycle.accept(project.root, "add-limit", DAY)
    lifecycle.tick(project.root, "add-limit", "1.1")
    lifecycle.self_review(project.root, "add-limit", "fine", DAY)
    lifecycle.archive(project.root, "add-limit", DAY, built="Shipped.")
    assert milestone_findings(project) == []


def after_named(other: str) -> str:
    return proposal().replace("- Owner: Sam Doe\n", f"- Owner: Sam Doe\n- After: {other}\n")


def after_findings(project: Workspace) -> list[tuple[str, str, str, int, str]]:
    return [
        (f.severity.value, f.path, f.code, f.line, f.message)
        for f in check(project.root, NOW)
        if "after" in f.code
    ]


def test_an_after_line_naming_another_change_is_healthy(project: Workspace) -> None:
    project.change("add-limit")
    project.change("add-paging", proposal_text=after_named("add-limit"))
    assert after_findings(project) == []


def test_scenario_unknown_change_named(project: Workspace) -> None:
    project.change("add-limit", proposal_text=after_named("no-such-change"))
    [(severity, path, code, line, message)] = after_findings(project)
    assert (severity, path, code, line) == (
        "error",
        "changes/add-limit/proposal.md",
        "unknown-after",
        4,
    )
    assert '"no-such-change"' in message


def test_an_after_line_may_name_an_archived_change(project: Workspace) -> None:
    project.write("changes/archive/2026-01-20-add-index/proposal.md", proposal(outcome="Done."))
    project.change("add-limit", proposal_text=after_named("add-index"))
    found = after_findings(project)
    assert [code for severity, _, code, _, _ in found if severity == "error"] == []


def test_a_change_after_itself(project: Workspace) -> None:
    project.change("add-limit", proposal_text=after_named("add-limit"))
    assert [code for _, _, code, _, _ in after_findings(project)] == ["after-self"]


def test_scenario_cycle(project: Workspace) -> None:
    project.change("add-a", proposal_text=after_named("add-b"))
    project.change("add-b", proposal_text=after_named("add-a"))
    found = after_findings(project)
    assert sorted((path, code) for _, path, code, _, _ in found) == [
        ("changes/add-a/proposal.md", "after-cycle"),
        ("changes/add-b/proposal.md", "after-cycle"),
    ]
    assert "add-a -> add-b -> add-a" in found[0][4]


def test_scenario_dependency_merged(project: Workspace) -> None:
    """Requirement "Merged base reported": a change after an archived one is warned about."""
    project.write("changes/archive/2026-01-20-add-limit/proposal.md", proposal(outcome="Done."))
    project.change("add-paging", proposal_text=after_named("add-limit"))
    [(severity, path, code, line, message)] = after_findings(project)
    assert (severity, path, code, line) == (
        "warning",
        "changes/add-paging/proposal.md",
        "after-merged",
        4,
    )
    assert '"add-limit"' in message
    assert "Rebase" in message
    assert "pull request" in message
    assert '"- After:"' in message


def test_an_unmerged_dependency_is_not_warned_about(project: Workspace) -> None:
    project.change("add-limit")
    project.change("add-paging", proposal_text=after_named("add-limit"))
    assert after_findings(project) == []

"""Task lists: the Log section, holding every record, and records misplaced under items."""

import datetime

from tests.support import Workspace, document
from waymark.record.artifacts.tasks import Tasks, parse_tasks
from waymark.record.evidence.fingerprint import change_fingerprint
from waymark.record.evidence.records import RecordKind
from waymark.record.state import AcceptanceState, acceptance_state
from waymark.record.terms import BuildRole, ReviewSeverity, Verdict

HEAD = "# Tasks\n\n## 1. Limit\n\n"
ITEM = (
    "- [ ] 1.1 Cap it\n  - **Build:** planner\n  - **Criteria:** fifty at most\n"
    "  - **Verify:** a test\n"
)


def parse(text: str) -> Tasks:
    return parse_tasks(document(text, "changes/add-limit/tasks.md"))


def codes(text: str) -> list[str]:
    return [problem.code for problem in parse(text).problems]


def test_scenario_record_under_an_item() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + "  - 2026-11-20 (blocked) by Ada: the API key is missing\n"
        + "  - 2026-11-20 (note) by Ada: halfway\n"
    )
    assert [(problem.code, problem.line) for problem in tasks.problems] == [
        ("misplaced-record", 9),
        ("misplaced-record", 10),
    ]
    assert "belong in the Log section" in tasks.problems[0].message
    item = tasks.items[0]
    assert (item.records, item.blocked, item.notes) == ((), None, ())
    assert item.criteria == "fifty at most"


def test_a_gap_after_a_resolution_is_open_again() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + "\n## Log\n\n"
        + "- 2026-11-20 (gap) 1.1: the maximum\n"
        + "- 2026-11-21 (resolved) 1.1: fifty\n"
        + "- 2026-11-22 (gap) 1.1: the default\n"
    )
    assert tasks.problems == ()
    assert tasks.items[0].spec_gap == "the default"


def test_the_log_holds_the_change_records_and_their_findings() -> None:
    tasks = parse(
        HEAD
        + "- [x] 1.1 Cap it\n  - **Build:** planner\n\n## Log\n\n"
        + "- 2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 items 1.1 by Ada\n"
        + "- 2026-11-21 (synced) by Ada\n"
        + "- 2026-11-22 (review) changes 1.1 by reviewer: the cap is off by one\n"
        + "  - [critical] `src/a.py:12`: fifty-one come back\n"
    )
    assert tasks.problems == ()
    assert [record.kind for record in tasks.log] == [
        RecordKind.ACCEPTED,
        RecordKind.SYNCED,
        RecordKind.REVIEW,
    ]
    accepted = tasks.latest(RecordKind.ACCEPTED)
    assert accepted is not None
    assert (accepted.fingerprint, accepted.covers, accepted.who) == (
        "81577cca8ff3ca11",
        ("1.1",),
        "Ada",
    )
    [review] = tasks.review_records
    assert review.verdict is Verdict.CHANGES
    assert review.items == ("1.1",)
    assert [(f.severity, f.place) for f in review.findings] == [
        (ReviewSeverity.CRITICAL, "src/a.py:12")
    ]


def test_scenario_malformed_record_under_an_item() -> None:
    tasks = parse(HEAD + ITEM + "  - (blocked) the API key is missing\n")
    [problem] = tasks.problems
    assert problem.code == "malformed-record"
    assert "YYYY-MM-DD (blocked) <item> [by <who>]: <reason>" in problem.message


def test_records_in_the_wrong_place_are_reported() -> None:
    assert codes(
        HEAD + ITEM + "  - 2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 items 1.1\n"
    ) == ["misplaced-record"]
    assert codes(HEAD + ITEM + "  - 2026-11-20 (note) 1.2: elsewhere\n") == ["misplaced-record"]


LOG = "\n## Log\n\n"
TWO_ITEMS = ITEM + ITEM.replace("1.1 Cap it", "1.2 Page it")


def test_an_item_record_in_the_log_names_its_item() -> None:
    tasks = parse(HEAD + ITEM + LOG + "- 2026-11-20 (blocked): the key\n")
    [problem] = tasks.problems
    assert problem.code == "malformed-record"
    assert "YYYY-MM-DD (blocked) <item> [by <who>]: <reason>" in problem.message
    assert codes(HEAD + ITEM + LOG + "- 2026-11-20 (blocked) 1.1 1.2: the key\n") == [
        "malformed-record"
    ]


def test_an_item_record_naming_an_unknown_item_is_reported() -> None:
    tasks = parse(HEAD + ITEM + LOG + "- 2026-11-20 (note) 9.9 by Ada: elsewhere\n")
    [problem] = tasks.problems
    assert problem.code == "unknown-item"
    assert "9.9" in problem.message


def test_item_records_are_gathered_from_the_log_in_order() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + LOG
        + "- 2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 items 1.1 by Ada\n"
        + "- 2026-11-20 (blocked) 1.1 by Ada: the API key is missing\n"
        + "- 2026-11-21 (note) 1.1 by implementer: partial: the parser is done\n"
        + "- 2026-11-22 (reopened) 1.1 by Ada\n"
    )
    assert tasks.problems == ()
    item = tasks.items[0]
    assert [record.kind for record in item.records] == [
        RecordKind.BLOCKED,
        RecordKind.NOTE,
        RecordKind.REOPENED,
    ]
    assert {record.item for record in item.records} == {"1.1"}
    assert item.blocked == "the API key is missing"
    assert item.notes == ("partial: the parser is done",)
    assert [record.kind for record in tasks.log] == [
        RecordKind.ACCEPTED,
        RecordKind.BLOCKED,
        RecordKind.NOTE,
        RecordKind.REOPENED,
    ]


def test_scenario_resolved_item_keeps_its_blocker_in_the_log() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + LOG
        + "- 2026-11-20 (blocked) 1.1 by Ada: the API key is missing\n"
        + "- 2026-11-21 (resolved) 1.1 by Sam: use the test key\n"
    )
    assert tasks.problems == ()
    item = tasks.items[0]
    assert item.blocked is None
    assert [record.kind for record in item.records] == [RecordKind.BLOCKED, RecordKind.RESOLVED]
    assert [record.kind for record in tasks.log] == [RecordKind.BLOCKED, RecordKind.RESOLVED]


def test_scenario_records_for_two_items() -> None:
    tasks = parse(
        HEAD
        + TWO_ITEMS
        + LOG
        + "- 2026-11-20 (blocked) 1.1 by Ada: no key\n"
        + "- 2026-11-20 (blocked) 1.2 by Ada: no page size\n"
        + "- 2026-11-21 (resolved) 1.2 by Sam: twenty\n"
    )
    assert tasks.problems == ()
    first, second = tasks.items
    assert first.blocked == "no key"
    assert second.blocked is None
    assert [record.kind for record in first.records] == [RecordKind.BLOCKED]


def test_a_resolved_item_record_does_not_resolve_the_review() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + LOG
        + "- 2026-11-20 (review) spec-gap by reviewer: the cap is unclear\n"
        + "- 2026-11-21 (resolved) 1.1 by Sam: fifty\n"
    )
    assert tasks.problems == ()
    assert [record.kind for record in tasks.review_records] == [RecordKind.REVIEW]
    assert tasks.latest(RecordKind.RESOLVED) is None
    assert [record.text for record in tasks.items[0].records] == ["fifty"]


def test_milestone_records_in_a_task_list_are_reported() -> None:
    assert codes(HEAD + ITEM + "  - 2026-11-20 (proposed) add-cache\n") == ["misplaced-record"]
    assert codes(HEAD + ITEM + "\n## Log\n\n- 2026-11-20 (archived) add-cache\n") == [
        "misplaced-record"
    ]


def test_the_log_section_comes_last() -> None:
    text = (
        HEAD
        + ITEM
        + "\n## Log\n\n- 2026-11-20 (synced)\n\n## 2. Docs\n\n- [ ] 2.1 Say so\n"
        + "  - **Build:** planner\n"
    )
    assert codes(text) == ["log-section-last"]


def test_a_changes_verdict_names_items_the_task_list_has() -> None:
    assert codes(HEAD + ITEM + "\n## Log\n\n- 2026-11-20 (review) changes 9.9: wrong\n") == [
        "unknown-item"
    ]
    assert codes(HEAD + ITEM + "\n## Log\n\n- 2026-11-20 (review) changes: wrong\n") == [
        "changes-without-items"
    ]


def _accept_in_log(workspace: Workspace, items: list[str], fingerprint: str) -> None:
    covered = f" items {' '.join(items)}" if items else ""
    text = workspace.read("changes/add-limit/tasks.md")
    workspace.write(
        "changes/add-limit/tasks.md",
        text + f"\n## Log\n\n- 2026-11-20 (accepted) fingerprint {fingerprint}{covered} by Ada\n",
    )


def test_acceptance_comes_from_the_latest_accepted_record(workspace: Workspace) -> None:
    workspace.change()
    record = workspace.record()
    change = record.changes["add-limit"]
    fingerprint = change_fingerprint(change, record.specs, record.default_review, ["1.1", "1.2"])
    _accept_in_log(workspace, ["1.1", "1.2"], "0" * 16)
    workspace.replace(
        "changes/add-limit/tasks.md",
        "by Ada\n",
        f"by Ada\n- 2026-11-21 (accepted) fingerprint {fingerprint} items 1.1, 1.2 by Ada\n",
    )
    record = workspace.record()
    change = record.changes["add-limit"]
    assert change.acceptance is not None
    assert change.acceptance.date == datetime.date(2026, 11, 21)
    assert acceptance_state(record, change) is AcceptanceState.VALID


PLANNED = (
    "# Tasks\n\n## 1. Limit\n\n"
    "- [ ] 1.1 Cap it\n  - **Build:** planner\n  - **Criteria:** fifty at most\n"
    "  - **Verify:** a test\n"
    "- [ ] 1.2 Rebuild the index\n  - **Build:** planner\n  - **Criteria:** rebuilt\n"
    "  - **Verify:** the index answers\n"
)


def test_build_values_are_read() -> None:
    """Requirement "Build line": the line names one of three roles; no line is no role."""
    tasks = parse(
        PLANNED.replace(
            "**Build:** planner\n  - **Criteria:** rebuilt",
            "**Build:** implementer\n  - **Criteria:** rebuilt",
        )
    )
    assert tasks.problems == ()
    assert [item.build for item in tasks.items] == [BuildRole.PLANNER, BuildRole.IMPLEMENTER]
    bare = parse(PLANNED.replace("  - **Build:** planner\n", ""))
    assert [item.build for item in bare.items] == [None, None]


def test_scenario_build_changed_after_acceptance(workspace: Workspace) -> None:
    """Requirement "Build line accepted with the item": changing the value withdraws acceptance."""
    workspace.change(tasks=PLANNED)
    workspace.accept()
    assert workspace.change_state().acceptance is AcceptanceState.VALID
    workspace.replace(
        "changes/add-limit/tasks.md",
        "  - **Build:** planner\n  - **Criteria:** rebuilt",
        "  - **Build:** implementer\n  - **Criteria:** rebuilt",
    )
    assert workspace.change_state().acceptance is AcceptanceState.WITHDRAWN


def test_an_item_without_a_build_line_hashes_as_before(workspace: Workspace) -> None:
    """Adding planner Build lines changes the items' definitions; no line hashes as it did."""
    bare = PLANNED.replace("  - **Build:** planner\n", "")
    workspace.change(tasks=bare)
    record = workspace.record()
    change = record.changes["add-limit"]
    before = change_fingerprint(change, record.specs, record.default_review, ["1.1", "1.2"])
    workspace.change(tasks=bare.replace("  - **Criteria:** fifty", "  - **Criteria:** fifty"))
    record = workspace.record()
    same = change_fingerprint(
        record.changes["add-limit"], record.specs, record.default_review, ["1.1", "1.2"]
    )
    assert same == before
    workspace.change(tasks=PLANNED)
    record = workspace.record()
    planned = change_fingerprint(
        record.changes["add-limit"], record.specs, record.default_review, ["1.1", "1.2"]
    )
    assert planned != before

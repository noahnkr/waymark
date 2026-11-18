"""Task lists: records under items and the Log section."""

import datetime

from tests.support import Workspace, document
from waymark.record.fingerprint import change_fingerprint
from waymark.record.records import RecordKind
from waymark.record.state import AcceptanceState, acceptance_state
from waymark.record.tasks import Tasks, parse_tasks
from waymark.record.terms import ReviewSeverity, Verdict

HEAD = "# Tasks\n\n## 1. Limit\n\n"
ITEM = "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n  - Verify: a test\n"


def parse(text: str) -> Tasks:
    return parse_tasks(document(text, "changes/add-limit/tasks.md"))


def codes(text: str) -> list[str]:
    return [problem.code for problem in parse(text).problems]


def test_item_records_are_read_under_their_item() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + "  - (blocked) 2026-11-20 by Ada: the API key is missing\n"
        + "  - (note) 2026-11-20 by wm-implementer: partial: the parser is done\n"
    )
    assert tasks.problems == ()
    item = tasks.items[0]
    assert [record.kind for record in item.records] == [RecordKind.BLOCKED, RecordKind.NOTE]
    assert item.records[0].who == "Ada"
    assert item.blocked == "the API key is missing"
    assert item.notes == ("partial: the parser is done",)
    assert item.criteria == "fifty at most"


def test_scenario_resolved_item_keeps_its_blocker() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + "  - (blocked) 2026-11-20 by Ada: the API key is missing\n"
        + "  - (resolved) 2026-11-21 by Sam: use the test key\n"
    )
    item = tasks.items[0]
    assert item.blocked is None
    assert [record.kind for record in item.records] == [RecordKind.BLOCKED, RecordKind.RESOLVED]


def test_a_gap_after_a_resolution_is_open_again() -> None:
    tasks = parse(
        HEAD
        + ITEM
        + "  - (gap) 2026-11-20: the maximum\n"
        + "  - (resolved) 2026-11-21: fifty\n"
        + "  - (gap) 2026-11-22: the default\n"
    )
    assert tasks.items[0].spec_gap == "the default"


def test_the_log_holds_the_change_records_and_their_findings() -> None:
    tasks = parse(
        HEAD
        + "- [x] 1.1 Cap it\n\n## Log\n\n"
        + "- (accepted) 2026-11-20 fingerprint 81577cca8ff3ca11 items 1.1 by Ada\n"
        + "- (synced) 2026-11-21 by Ada\n"
        + "- (review) 2026-11-22 changes 1.1 by wm-reviewer: the cap is off by one\n"
        + "  - critical `src/a.py:12`: fifty-one come back\n"
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
    assert "(blocked) YYYY-MM-DD [by <who>]: <reason>" in problem.message


def test_records_in_the_wrong_place_are_reported() -> None:
    assert codes(
        HEAD + ITEM + "  - (accepted) 2026-11-20 fingerprint 81577cca8ff3ca11 items 1.1\n"
    ) == ["misplaced-record"]
    assert codes(HEAD + ITEM + "\n## Log\n\n- (blocked) 2026-11-20: the key\n") == [
        "misplaced-record"
    ]


def test_milestone_records_in_a_task_list_are_reported() -> None:
    assert codes(HEAD + ITEM + "  - (proposed) 2026-11-20 add-cache\n") == ["misplaced-record"]
    assert codes(HEAD + ITEM + "\n## Log\n\n- (archived) 2026-11-20 add-cache\n") == [
        "misplaced-record"
    ]


def test_the_log_section_comes_last() -> None:
    text = HEAD + ITEM + "\n## Log\n\n- (synced) 2026-11-20\n\n## 2. Docs\n\n- [ ] 2.1 Say so\n"
    assert codes(text) == ["log-section-last"]


def test_a_changes_verdict_names_items_the_task_list_has() -> None:
    assert codes(HEAD + ITEM + "\n## Log\n\n- (review) 2026-11-20 changes 9.9: wrong\n") == [
        "unknown-item"
    ]
    assert codes(HEAD + ITEM + "\n## Log\n\n- (review) 2026-11-20 changes: wrong\n") == [
        "changes-without-items"
    ]


def _accept_in_log(workspace: Workspace, items: list[str], fingerprint: str) -> None:
    covered = f" items {' '.join(items)}" if items else ""
    text = workspace.read("changes/add-limit/tasks.md")
    workspace.write(
        "changes/add-limit/tasks.md",
        text + f"\n## Log\n\n- (accepted) 2026-11-20 fingerprint {fingerprint}{covered} by Ada\n",
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
        f"by Ada\n- (accepted) 2026-11-21 fingerprint {fingerprint} items 1.1 1.2 by Ada\n",
    )
    record = workspace.record()
    change = record.changes["add-limit"]
    assert change.acceptance is not None
    assert change.acceptance.date == datetime.date(2026, 11, 21)
    assert acceptance_state(record, change) is AcceptanceState.VALID

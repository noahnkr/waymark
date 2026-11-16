"""Task lists in record format 2: records under items and the Log section."""

import datetime

from tests.support import CONFIG, Workspace, document
from waymark.record.fingerprint import change_fingerprint
from waymark.record.record import load_archived_change
from waymark.record.records import RecordKind
from waymark.record.state import AcceptanceState, acceptance_state
from waymark.record.tasks import Tasks, parse_tasks
from waymark.record.terms import ReviewSeverity, Verdict

HEAD = "# Tasks\n\n## 1. Limit\n\n"
ITEM = "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n  - Verify: a test\n"
FORMAT_2 = CONFIG.replace("record_format = 1", "record_format = 2")


def parse(text: str) -> Tasks:
    return parse_tasks(document(text, "changes/add-limit/tasks.md"), 2)


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


def test_old_lines_in_the_latest_format_say_to_run_update() -> None:
    assert codes(HEAD + ITEM + "  - Blocked: the key\n") == ["old-record-format"]
    assert codes(HEAD + ITEM + "  - Note: half done\n") == ["old-record-format"]
    assert codes(HEAD + ITEM + "\n## Review\n\n- (self-review) 2026-11-20: ok\n") == [
        "old-record-format"
    ]


def test_records_in_the_wrong_place_are_reported() -> None:
    assert codes(HEAD + ITEM + "  - (accepted) 2026-11-20 fingerprint 81577cca8ff3ca11\n") == [
        "misplaced-record"
    ]
    assert codes(HEAD + ITEM + "\n## Log\n\n- (blocked) 2026-11-20: the key\n") == [
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
    workspace.write("config.toml", FORMAT_2)
    workspace.change()
    record = workspace.record()
    change = record.changes["add-limit"]
    assert change.version == 2
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


def test_scenario_older_acceptance_line(workspace: Workspace) -> None:
    """An (accepted) record without items covers every item, so a new item withdraws it."""
    workspace.write("config.toml", FORMAT_2)
    workspace.change()
    record = workspace.record()
    change = record.changes["add-limit"]
    fingerprint = change_fingerprint(change, record.specs, record.default_review)
    _accept_in_log(workspace, [], fingerprint)
    assert acceptance_state(workspace.record(), workspace.record().changes["add-limit"]) is (
        AcceptanceState.VALID
    )
    workspace.replace(
        "changes/add-limit/tasks.md",
        "- [ ] 1.2 Document the limit\n",
        "- [ ] 1.2 Document the limit\n- [ ] 1.3 Test it\n",
    )
    record = workspace.record()
    change = record.changes["add-limit"]
    assert acceptance_state(record, change) is AcceptanceState.WITHDRAWN
    assert [p.code for p in change.problems] == []


def test_a_format_2_proposal_holds_no_records(workspace: Workspace) -> None:
    workspace.write("config.toml", FORMAT_2)
    workspace.change()
    workspace.replace(
        "changes/add-limit/proposal.md", "Owner: Sam Doe\n", "Owner: Sam Doe\nSynced: 2026-11-20\n"
    )
    change = workspace.record().changes["add-limit"]
    assert [p.code for p in change.problems] == ["old-record-format"]


def test_a_format_1_record_is_read_as_before(workspace: Workspace) -> None:
    workspace.change()
    workspace.replace(
        "changes/add-limit/tasks.md",
        "  - Verify: a test covers fifty-one matches\n",
        "  - Verify: a test covers fifty-one matches\n  - Blocked: the key\n",
    )
    workspace.accept()
    change = workspace.record().changes["add-limit"]
    assert change.version == 1
    assert change.tasks is not None
    assert change.tasks.items[0].blocked == "the key"
    assert change.acceptance is not None
    assert change.problems == ()


def test_an_archived_change_is_read_in_the_format_it_was_written(workspace: Workspace) -> None:
    workspace.write("config.toml", FORMAT_2)
    old = workspace.change("archive/2026-01-20-old-limit")
    workspace.replace(
        f"{old}/proposal.md",
        "Owner: Sam Doe\n",
        "Owner: Sam Doe\nAccepted: 2026-01-15 by Sam Doe (fingerprint: 0123456789abcdef)\n",
    )
    workspace.write(
        f"{old}/tasks.md",
        "# Tasks\n\n## 1. Limit\n\n- [x] 1.1 Cap it\n  - Note: done early\n\n"
        "## Review\n\n- (self-review) 2026-01-16: fine\n",
    )
    new = workspace.change("archive/2026-02-20-new-limit")
    workspace.write(
        f"{new}/tasks.md",
        "# Tasks\n\n## 1. Limit\n\n- [x] 1.1 Cap it\n\n## Log\n\n"
        "- (accepted) 2026-02-15 fingerprint 0123456789abcdef items 1.1 by Sam\n"
        "- (self-review) 2026-02-16 by Sam: fine\n",
    )
    record = workspace.record()
    by_name = {entry.name: entry for entry in record.archived_changes}
    old_change = load_archived_change(record, by_name["old-limit"])
    new_change = load_archived_change(record, by_name["new-limit"])
    assert (old_change.version, new_change.version) == (1, 2)
    assert old_change.problems == ()
    assert new_change.problems == ()
    assert old_change.tasks is not None
    assert new_change.tasks is not None
    assert old_change.tasks.items[0].notes == ("done early",)
    assert [r.kind for r in old_change.tasks.review_records] == [RecordKind.SELF_REVIEW]
    assert [r.kind for r in new_change.tasks.review_records] == [RecordKind.SELF_REVIEW]
    assert new_change.acceptance is not None
    assert new_change.acceptance.items == ("1.1",)

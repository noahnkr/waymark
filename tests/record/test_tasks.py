"""Task lists: items, their definitions and their evidence."""

import datetime

from tests.support import TASKS, document
from waymark.record.tasks import RecordKind, Tasks, is_evidence_line, parse_tasks
from waymark.record.terms import ReviewLevel, Verdict

HEAD = "# Tasks\n\n## 1. Limit\n\n"


def parse(text: str) -> Tasks:
    return parse_tasks(document(text, "changes/add-limit/tasks.md"))


def codes(text: str) -> list[str]:
    return [problem.code for problem in parse(text).problems]


def test_items_are_numbered_by_section_and_addressed_by_number() -> None:
    tasks = parse(TASKS + "\n## 2. Docs\n\n- [x] 2.1 Explain the limit\n")
    assert tasks.problems == ()
    assert [(section.number, section.title) for section in tasks.sections] == [
        (1, "Limit"),
        (2, "Docs"),
    ]
    assert [item.number for item in tasks.items] == ["1.1", "1.2", "2.1"]
    found = tasks.item("2.1")
    assert found is not None
    assert found.title == "Explain the limit"
    assert found.ticked
    assert tasks.item("9.9") is None


def test_item_carries_its_criteria_verification_and_repo() -> None:
    tasks = parse(
        HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n  - Verify: a test\n  - Repo: api\n"
    )
    (item,) = tasks.items
    assert (item.criteria, item.verify, item.repo) == ("fifty at most", "a test", "api")
    assert not item.ticked


def test_review_level_tag_overrides_the_project_default() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it   `review: independent`\n- [ ] 1.2 Tidy up\n")
    tagged, plain = tasks.items
    assert tagged.title == "Cap it"
    assert tagged.level(ReviewLevel.SELF) is ReviewLevel.INDEPENDENT
    assert plain.level_tag is None
    assert plain.level(ReviewLevel.SELF) is ReviewLevel.SELF
    assert plain.level(ReviewLevel.NONE) is ReviewLevel.NONE


def test_unknown_review_level_is_a_problem() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it   `review: strict`\n") == ["unknown-review-level"]


def test_review_records_sit_under_their_item() -> None:
    tasks = parse(
        HEAD
        + "- [x] 1.1 Cap it\n"
        + "  - (review) 2026-02-01 changes: the boundary is off by one\n"
        + "  - (reopened) 2026-02-02\n"
        + "  - (review) 2026-02-03 pass: boundary covered\n"
        + "- [x] 1.2 Tidy up\n"
        + "  - (self-review) 2026-02-04: matches the criteria\n"
    )
    assert tasks.problems == ()
    first, second = tasks.items
    assert [record.kind for record in first.records] == [
        RecordKind.REVIEW,
        RecordKind.REOPENED,
        RecordKind.REVIEW,
    ]
    assert first.records[0].verdict is Verdict.CHANGES
    assert first.records[0].text == "the boundary is off by one"
    assert first.records[2].date == datetime.date(2026, 2, 3)
    assert second.records[0].kind is RecordKind.SELF_REVIEW
    assert second.records[0].verdict is None


def test_review_record_that_breaks_the_format_is_malformed_evidence() -> None:
    assert codes(HEAD + "- [x] 1.1 Cap it\n  - (review) looks good to me\n") == [
        "malformed-evidence"
    ]
    assert codes(HEAD + "- [x] 1.1 Cap it\n  - (review) 2026-02-01 fine: ok\n") == [
        "malformed-evidence"
    ]
    assert codes(HEAD + "- [x] 1.1 Cap it\n  - (review) 2026-02-31 pass: ok\n") == [
        "malformed-evidence"
    ]
    assert codes(HEAD + "- [x] 1.1 Cap it\n  - (self-review) 2026-02-01\n") == [
        "malformed-evidence"
    ]


def test_blocked_line_sits_under_its_item() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it\n  - Blocked: waiting for the wording\n")
    assert tasks.items[0].blocked == "waiting for the wording"
    assert codes(HEAD + "- [ ] 1.1 Cap it\n  - Blocked:\n") == ["empty-field"]


def test_notes_are_kept_apart_from_the_definition() -> None:
    tasks = parse(
        HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n  - Note: tried a query cap first\n"
        "  - Note: sorting is stable\n"
    )
    (item,) = tasks.items
    assert item.criteria == "fifty at most"
    assert item.notes == ("tried a query cap first", "sorting is stable")


def test_field_may_continue_over_indented_lines() -> None:
    tasks = parse(
        HEAD
        + "- [ ] 1.1 Cap it\n  - Criteria:\n    - fifty at most\n    - order kept\n"
        + "  - Verify: a test\n"
    )
    assert tasks.problems == ()
    assert tasks.items[0].criteria == "- fifty at most\n- order kept"
    assert tasks.items[0].verify == "a test"


def test_item_number_matches_its_section() -> None:
    assert codes(HEAD + "- [ ] 2.1 Cap it\n") == ["item-number"]


def test_item_numbers_are_never_reused() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it\n- [ ] 1.1 Tidy up\n") == ["item-number"]
    assert codes(HEAD + "- [ ] 1.2 Cap it\n- [ ] 1.1 Tidy up\n") == ["item-number"]


def test_item_numbers_may_have_gaps() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it\n- [ ] 1.4 Tidy up\n") == []


def test_section_numbers_are_never_reused() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it\n\n## 1. Again\n") == ["section-number"]


def test_section_heading_must_be_numbered() -> None:
    assert codes("# Tasks\n\n## Limit\n") == ["task-section-format"]


def test_item_outside_a_section_is_a_problem() -> None:
    assert codes("# Tasks\n\n- [ ] 1.1 Cap it\n") == ["item-outside-section"]


def test_list_line_that_is_not_an_item_is_a_problem() -> None:
    assert codes(HEAD + "- [ ] Cap it\n") == ["malformed-item"]
    assert codes(HEAD + "- [] 1.1 Cap it\n") == ["malformed-item"]
    assert codes(HEAD + "- Cap it\n") == ["malformed-item"]


def test_prose_between_items_is_allowed() -> None:
    tasks = parse(HEAD + "Start with the query path.\n\n- [ ] 1.1 Cap it\n")
    assert tasks.problems == ()
    assert len(tasks.items) == 1


def test_unlabeled_line_under_an_item_is_a_problem() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it\n  - fifty at most\n") == ["unrecognized-item-line"]
    assert codes(HEAD + "- [ ] 1.1 Cap it\n  - Criterion: fifty at most\n") == [
        "unrecognized-item-line"
    ]


def test_field_given_twice_is_a_problem() -> None:
    assert codes(HEAD + "- [ ] 1.1 Cap it\n  - Criteria: a\n  - Criteria: b\n") == [
        "duplicate-field"
    ]


def test_evidence_lines_are_blockers_and_review_records() -> None:
    assert is_evidence_line("  - Blocked: waiting")
    assert is_evidence_line("  - (review) 2026-02-01 pass: fine")
    assert is_evidence_line("  - (self-review) anything at all")
    assert is_evidence_line("  - (reopened) 2026-02-01")
    assert not is_evidence_line("  - Criteria: fifty at most")
    assert not is_evidence_line("  - Note: (review) is mentioned here")
    assert not is_evidence_line("- [x] 1.1 Cap it")

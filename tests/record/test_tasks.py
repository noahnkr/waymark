"""Task lists: items, their definitions and their evidence."""

import datetime

import pytest

from tests.support import TASKS, document
from waymark.record.evidence import evidence_changes
from waymark.record.tasks import RecordKind, Tasks, is_evidence_line, parse_tasks
from waymark.record.terms import ReviewLevel, ReviewSeverity, Verdict

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


def test_build_tag_marks_an_item_for_delegation_in_either_order() -> None:
    tasks = parse(
        HEAD
        + "- [ ] 1.1 Cap it   `review: independent`   `build: delegate`\n"
        + "- [ ] 1.2 Page it   `build: delegate`   `review: none`\n"
        + "- [ ] 1.3 Sort it   `build: delegate`\n"
        + "- [ ] 1.4 Tidy up\n"
    )
    assert tasks.problems == ()
    first, second, third, plain = tasks.items
    assert [item.title for item in tasks.items] == ["Cap it", "Page it", "Sort it", "Tidy up"]
    assert (first.delegate, first.level_tag) == (True, ReviewLevel.INDEPENDENT)
    assert (second.delegate, second.level_tag) == (True, ReviewLevel.NONE)
    assert (third.delegate, third.level_tag) == (True, None)
    assert (plain.delegate, plain.level_tag) == (False, None)


def test_unknown_build_tag_is_a_problem_that_names_delegate() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it   `build: someone`\n")
    (problem,) = tasks.problems
    assert problem.code == "unknown-build-tag"
    assert '"someone"' in problem.message
    assert "The only value is: delegate." in problem.message
    (item,) = tasks.items
    assert item.title == "Cap it"
    assert not item.delegate


@pytest.mark.parametrize(
    "tags",
    [
        "`build: delegate`   `build: delegate`",
        "`review: none`   `build: delegate`   `review: self`",
    ],
)
def test_repeated_tag_is_a_problem(tags: str) -> None:
    tasks = parse(HEAD + f"- [ ] 1.1 Cap it   {tags}\n")
    assert [problem.code for problem in tasks.problems] == ["repeated-tag"]
    assert tasks.items[0].title == "Cap it"


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


REVIEWED = (
    HEAD
    + "- [x] 1.1 Cap it\n"
    + "- [x] 1.2 Tidy up\n"
    + "\n## Review\n\n"
    + "- (review) 2026-02-01 changes 1.1 1.2: the boundary is off by one\n"
    + "  - critical: src/search.py:12: fifty-one results come back\n"
    + "  - suggestion: docs/search.md: say the limit\n"
    + "- (self-review) 2026-02-03: matches the criteria\n"
    + "- (resolved) 2026-02-04: keep fifty\n"
)


def test_review_section_holds_the_change_records_and_their_findings() -> None:
    tasks = parse(REVIEWED)
    assert tasks.problems == ()
    assert [item.records for item in tasks.items] == [(), ()]
    first, second, third = tasks.review_records
    assert (first.kind, first.verdict, first.items) == (
        RecordKind.REVIEW,
        Verdict.CHANGES,
        ("1.1", "1.2"),
    )
    assert first.text == "the boundary is off by one"
    assert [(f.severity, f.place, f.text) for f in first.findings] == [
        (ReviewSeverity.CRITICAL, "src/search.py:12", "fifty-one results come back"),
        (ReviewSeverity.SUGGESTION, "docs/search.md", "say the limit"),
    ]
    assert (second.kind, second.text, second.findings) == (
        RecordKind.SELF_REVIEW,
        "matches the criteria",
        (),
    )
    assert (third.kind, third.date) == (RecordKind.RESOLVED, datetime.date(2026, 2, 4))
    assert tasks.review_section is not None


@pytest.mark.parametrize(
    ("record", "code"),
    [
        ("- (review) 2026-02-01 changes: off by one", "changes-without-items"),
        ("- (review) 2026-02-01 pass 1.1: fine", "items-without-changes"),
        ("- (review) 2026-02-01 changes 9.9: off by one", "unknown-item"),
        ("- (reopened) 2026-02-01", "malformed-evidence"),
        ("- (review) 2026-02-01 pass: fine\n  - severe: here: bad", "malformed-finding"),
        ("- (resolved) 2026-02-01: keep it\n  - warning: here: odd", "misplaced-finding"),
        ("Looks good to me.", "unrecognized-review-line"),
    ],
)
def test_review_section_lines_that_break_the_format_are_problems(record: str, code: str) -> None:
    assert codes(HEAD + "- [x] 1.1 Cap it\n\n## Review\n\n" + record + "\n") == [code]


def test_review_section_comes_last() -> None:
    text = HEAD + "- [x] 1.1 Cap it\n\n## Review\n\n## 2. Docs\n\n- [ ] 2.1 Explain\n"
    assert codes(text) == ["review-section-last"]


def test_every_line_of_the_review_section_is_evidence() -> None:
    before = HEAD + "- [x] 1.1 Cap it\n"
    after = before + "\n## Review\n\n- (self-review) 2026-02-03: fine\n  - warning: a.py: odd\n"
    assert evidence_changes("changes/add-limit/tasks.md", before, after) == [
        'adds "- (self-review) 2026-02-03: fine" in the Review section',
        'adds "- warning: a.py: odd" in the Review section',
    ]

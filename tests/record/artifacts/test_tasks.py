"""Task lists: items, their definitions and their evidence."""

from tests.support import TASKS, document
from waymark.record.artifacts.tasks import Tasks, parse_tasks

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


def test_build_tag_marks_an_item_for_delegation() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Sort it\n  - Build: delegate\n- [ ] 1.2 Tidy up\n")
    assert tasks.problems == ()
    tagged, plain = tasks.items
    assert [item.title for item in tasks.items] == ["Sort it", "Tidy up"]
    assert (tagged.delegate, plain.delegate) == (True, False)


def test_unknown_build_tag_is_a_problem_that_names_delegate() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it\n  - Build: someone\n")
    (problem,) = tasks.problems
    assert problem.code == "unknown-build-tag"
    assert '"someone"' in problem.message
    assert "The only value is: delegate." in problem.message
    (item,) = tasks.items
    assert item.title == "Cap it"
    assert not item.delegate


def test_a_trailing_build_tag_stays_part_of_the_title() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it   `build: delegate`\n")
    assert tasks.problems == ()
    assert tasks.items[0].title == "Cap it   `build: delegate`"
    assert not tasks.items[0].delegate


def test_the_build_line_given_twice_is_a_problem() -> None:
    tasks = parse(HEAD + "- [ ] 1.1 Cap it\n  - Build: delegate\n  - Build: delegate\n")
    assert [problem.code for problem in tasks.problems] == ["duplicate-field"]


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

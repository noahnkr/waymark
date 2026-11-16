"""The standard layout: what wm check --fix writes, and what it never touches."""

import pytest

from waymark.record.layout import Fix, standard_layout


def fixed(text: str) -> str:
    return standard_layout(text)[0]


def test_list_markers_become_dashes() -> None:
    text, fixes = standard_layout("# T\n\n* one\n+ two\n  * nested\n")
    assert text == "# T\n\n- one\n- two\n  - nested\n"
    assert fixes == (Fix.LIST_MARKERS,)


def test_emphasis_and_thematic_breaks_are_not_list_markers() -> None:
    text = "# T\n\n*Note*: as is.\n\n* * *\n\n**bold** start\n"
    assert fixed(text) == text


def test_one_blank_line_before_each_heading_and_at_most_one_after() -> None:
    text, fixes = standard_layout("# T\nIntro\n\n\n## A\n\n\n\nBody\n## B\nEnd\n")
    assert text == "# T\nIntro\n\n## A\n\nBody\n\n## B\nEnd\n"
    assert fixes == (Fix.HEADING_SPACING,)


def test_a_requirement_keeps_its_text_directly_under_its_heading() -> None:
    text = (
        "## Requirements\n\n"
        "### Requirement: R\nThe system SHALL cap.\n\n"
        "#### Scenario: S\n- GIVEN x\n"
    )
    assert standard_layout(text) == (text, ())


def test_trailing_spaces_go() -> None:
    text, fixes = standard_layout("# T\n\nA line.  \nAnother\t\n")
    assert text == "# T\n\nA line.\nAnother\n"
    assert fixes == (Fix.TRAILING_SPACES,)


def test_the_file_ends_with_exactly_one_line_break() -> None:
    assert standard_layout("# T\n\nText") == ("# T\n\nText\n", (Fix.FINAL_LINE_BREAK,))
    assert standard_layout("# T\n\nText\n\n\n") == ("# T\n\nText\n", (Fix.FINAL_LINE_BREAK,))


def test_record_lines_take_their_standard_shape() -> None:
    text = (
        "# Tasks\n\n## Log\n\n"
        "- (review)  2026-11-20  pass   by  Ada: fine\n"
        "  - warning  `a.py:1`: vague\n"
    )
    result, fixes = standard_layout(text)
    assert result == (
        "# Tasks\n\n## Log\n\n"
        "- (review) 2026-11-20 pass by Ada: fine\n"
        "  - warning `a.py:1`: vague\n"
    )
    assert fixes == (Fix.RECORD_LINES,)


def test_a_line_that_does_not_parse_as_a_record_is_left_as_written() -> None:
    text = "# Tasks\n\n## Log\n\n- (blocked) the key\n"
    assert fixed(text) == text


def test_scenario_fenced_code_left_alone() -> None:
    text = "# Design\n\n```\n* item  \n\n\n## not a heading\n```\n"
    assert fixed(text) == text


def test_comments_are_left_alone() -> None:
    text = "# T\n\n<!-- * keep  \n## not a heading\n-->\n\n* fix\n"
    assert fixed(text) == "# T\n\n<!-- * keep  \n## not a heading\n-->\n\n- fix\n"


def test_wording_is_never_changed() -> None:
    text = "# T\n\nSome  double  spaced   words, a [link](a.md) and `code  span`.\n"
    assert fixed(text) == text


def test_line_endings_are_kept() -> None:
    text = "# T\r\nIntro  \r\n* a\r\n"
    assert fixed(text) == "# T\r\nIntro\r\n- a\r\n"


def test_a_byte_order_mark_is_kept() -> None:
    assert fixed("﻿# T\nText") == "﻿# T\nText\n"


@pytest.mark.parametrize(
    "text",
    [
        "# T\nIntro\n\n\n## A\n* x  \n+ y\n\n```\n* z  \n```\n",
        "# T\r\n\r\n\r\n## A\r\nText",
        "﻿# T\n- (note)  2026-11-20: x\n",
        "",
        "\n\n",
        "No heading at all  \n",
    ],
)
def test_the_layout_is_idempotent(text: str) -> None:
    once = fixed(text)
    assert standard_layout(once) == (once, ())


def test_a_file_in_layout_reports_no_fix() -> None:
    text = "# T\n\n## A\n\n- one\n"
    assert standard_layout(text) == (text, ())

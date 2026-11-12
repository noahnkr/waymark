"""Markdown handling: line endings, fences, headings, sections and links."""

from tests.support import document


def test_lines_keep_their_line_endings() -> None:
    text = "one\r\ntwo\nthree\rfour"
    doc = document(text)
    assert [line.ending for line in doc.lines] == ["\r\n", "\n", "\r", ""]
    assert "".join(doc.raw_lines()) == text


def test_newline_is_the_ending_of_the_first_line() -> None:
    assert document("a\r\nb\n").newline == "\r\n"
    assert document("a").newline == "\n"


def test_byte_order_mark_is_kept_out_of_the_title_and_restored() -> None:
    text = "﻿# Title\n"
    doc = document(text)
    assert doc.title is not None
    assert doc.title.title == "Title"
    assert "".join(doc.raw_lines()) == text


def test_headings_inside_code_fences_are_not_headings() -> None:
    doc = document("# Real\n\n```\n# Not one\n```\n\n~~~~\n## Nor this\n~~~~\n\n## Also real\n")
    assert [heading.title for heading in doc.headings] == ["Real", "Also real"]


def test_section_ends_at_the_next_heading_of_its_level_or_above() -> None:
    doc = document("# T\n## A\ntext\n### A1\nmore\n## B\nend\n")
    first, second = doc.sections(2)
    assert (first.title, first.start, first.end) == ("A", 1, 5)
    assert (second.title, second.end) == ("B", 7)
    assert [section.title for section in doc.sections(3, first.body_start, first.end)] == ["A1"]


def test_section_text_drops_comments_and_surrounding_blank_lines() -> None:
    doc = document("## A\n\n<!-- a hint\nover two lines -->\n\nkept\n\n")
    assert doc.body(doc.sections(2)[0]) == "kept"


def test_section_text_uses_line_feeds_whatever_the_file_uses() -> None:
    doc = document("## A\r\none\r\ntwo\r\n")
    assert doc.body(doc.sections(2)[0]) == "one\ntwo"


def test_links_are_found_with_their_position() -> None:
    doc = document("See [the spec](../specs/search.md#limit) and ![shot](shot.png).\n")
    first, second = doc.links()
    assert first.target == "../specs/search.md#limit"
    assert doc.lines[0].text[first.start : first.end] == first.target
    assert second.target == "shot.png"


def test_links_in_code_fences_and_code_spans_are_ignored() -> None:
    doc = document("`[a](gone.md)` and [b](here.md)\n\n```\n[c](gone.md)\n```\n")
    assert [link.target for link in doc.links()] == ["here.md"]


def test_reference_links_are_found() -> None:
    doc = document("[spec]: ../specs/search.md\n[^1]: a footnote, not a link\n")
    assert [link.target for link in doc.links()] == ["../specs/search.md"]


def test_checkboxes_are_not_links() -> None:
    assert document("- [x] 1.1 Do it (see notes)\n- [ ] 1.2 Next\n").links() == ()

"""The marked block in .gitignore: added, replaced in place, and left alone when current."""

from waymark.record.writing.ignore import BEGIN, END, merged, render

HOOKS = ["/.waymark/hooks/"]
PROJECT = ["/.agents/skills/wm-*/", "/.claude/skills/wm-*/", "/.waymark/hooks/"]

BLOCK = f"{BEGIN}\n/.agents/skills/wm-*/\n/.claude/skills/wm-*/\n/.waymark/hooks/\n{END}\n"


def test_render_lists_each_pattern_between_the_markers() -> None:
    assert render(PROJECT) == BLOCK


def test_new_project_without_an_ignore_file_gets_the_block() -> None:
    assert merged(None, PROJECT) == BLOCK
    assert merged("", PROJECT) == BLOCK


def test_existing_ignore_file_gets_the_block_at_the_end() -> None:
    own = "# build output\ndist/\n*.pyc\n"
    assert merged(own, PROJECT) == own + "\n" + BLOCK


def test_existing_ignore_file_ending_in_a_blank_line_gets_no_second_one() -> None:
    own = "dist/\n\n"
    assert merged(own, PROJECT) == own + BLOCK


def test_missing_final_newline_gets_one_before_the_block() -> None:
    assert merged("dist/\n*.pyc", PROJECT) == "dist/\n*.pyc\n\n" + BLOCK


def test_crlf_file_keeps_its_lines_and_the_block_takes_crlf() -> None:
    own = "dist/\r\n*.pyc\r\n"
    result = merged(own, PROJECT)
    assert result == own + "\r\n" + BLOCK.replace("\n", "\r\n")
    assert merged(result, PROJECT) == result


def test_block_already_current_leaves_the_text_unchanged() -> None:
    current = "dist/\n\n" + BLOCK + "\n# after\nbuild/\n"
    assert merged(current, PROJECT) == current


def test_block_out_of_date_is_replaced_in_place() -> None:
    before = "dist/\r\n\r\n"
    after = "\r\n# after\r\nbuild/"
    current = before + render(HOOKS, "\r\n") + after
    assert merged(current, PROJECT) == before + BLOCK.replace("\n", "\r\n") + after


def test_block_at_the_end_without_a_final_newline_keeps_it_missing() -> None:
    current = "dist/\n\n" + render(HOOKS).rstrip("\n")
    assert merged(current, PROJECT) == "dist/\n\n" + BLOCK.rstrip("\n")


def test_block_at_the_start_keeps_a_byte_order_mark() -> None:
    current = "﻿" + render(HOOKS) + "dist/\n"
    assert merged(current, PROJECT) == "﻿" + BLOCK + "dist/\n"


def test_block_without_its_closing_marker_stops_at_a_blank_line() -> None:
    current = f"{BEGIN}\n/.waymark/hooks/\n\ndist/\n"
    assert merged(current, PROJECT) == BLOCK + "\ndist/\n"


def test_merging_twice_changes_nothing() -> None:
    once = merged("dist/", HOOKS)
    assert merged(once, HOOKS) == once

"""Records: one shape for every line wm writes, read and written in one place."""

import datetime
from pathlib import Path

import pytest

from tests.conftest import git_init
from waymark.record.records import (
    KINDS,
    Finding,
    ParseError,
    Record,
    RecordError,
    RecordKind,
    looks_like_record,
    parse,
    parse_finding,
    parse_finding_argument,
    render,
    render_finding,
    shape,
    who_for,
)
from waymark.record.terms import ReviewSeverity, Verdict

DAY = datetime.date(2026, 11, 20)

ONE_OF_EACH = [
    Record(
        RecordKind.ACCEPTED,
        DAY,
        who="Ada Lovelace",
        fingerprint="81577cca8ff3ca11",
        items=("1.1", "1.2"),
    ),
    Record(RecordKind.ACCEPTED, DAY, who="Ada", fingerprint="81577cca8ff3ca11"),
    Record(RecordKind.SYNCED, DAY, who="Ada Lovelace"),
    Record(RecordKind.SYNCED, DAY, who="Ada", fingerprint="0123456789abcdef"),
    Record(RecordKind.OVERRIDE, DAY, who="Ada", text="the reviewer is away"),
    Record(RecordKind.SELF_REVIEW, DAY, who="Ada and Grace", text="every scenario holds"),
    Record(RecordKind.REVIEW, DAY, who="wm-reviewer", verdict=Verdict.PASS, text="fine"),
    Record(
        RecordKind.REVIEW,
        DAY,
        who="wm-reviewer",
        verdict=Verdict.CHANGES,
        items=("1.2", "2.1"),
        text="the limit is not checked",
    ),
    Record(RecordKind.REVIEW, DAY, verdict=Verdict.SPEC_GAP, text="the limit is unspecified"),
    Record(RecordKind.RESOLVED, DAY, who="Ada", text="use the test key: it is enough"),
    Record(RecordKind.REOPENED, DAY, who="Ada Lovelace"),
    Record(RecordKind.REOPENED, DAY),
    Record(RecordKind.BLOCKED, DAY, who="Ada", text="the API key is missing"),
    Record(RecordKind.GAP, DAY, text="the limit's maximum"),
    Record(RecordKind.NOTE, DAY, who="wm-implementer", text="partial: the parser is done"),
]


@pytest.mark.parametrize("record", ONE_OF_EACH, ids=render)
def test_one_record_shape(record: Record) -> None:
    """Requirement "One record shape": every kind renders and reads back the same."""
    assert parse(render(record)) == record


def test_one_record_shape_puts_the_arguments_before_who_wrote_it() -> None:
    assert render(ONE_OF_EACH[0]) == (
        "(accepted) 2026-11-20 fingerprint 81577cca8ff3ca11 items 1.1 1.2 by Ada Lovelace"
    )
    assert render(ONE_OF_EACH[7]) == (
        "(review) 2026-11-20 changes 1.2 2.1 by wm-reviewer: the limit is not checked"
    )
    assert render(ONE_OF_EACH[10]) == "(reopened) 2026-11-20 by Ada Lovelace"
    assert render(ONE_OF_EACH[11]) == "(reopened) 2026-11-20"
    assert render(ONE_OF_EACH[12]) == "(blocked) 2026-11-20 by Ada: the API key is missing"


def test_scenario_blocked_item() -> None:
    record = Record(RecordKind.BLOCKED, DAY, who="Ada", text="the API key is missing")
    assert render(record) == "(blocked) 2026-11-20 by Ada: the API key is missing"


def test_scenario_malformed_record() -> None:
    found = parse("(blocked) the API key is missing")
    assert isinstance(found, ParseError)
    assert found.kind is RecordKind.BLOCKED
    assert "(blocked) YYYY-MM-DD [by <who>]: <reason>" in found.message


@pytest.mark.parametrize(
    "text",
    [
        "(blocked) 2026-11-20",
        "(blocked) 2026-11-20 by Ada",
        "(blocked) 2026-11-20 by : reason",
        "(blocked) 2026-11-20 soon: reason",
        "(blocked) 2026-11-20:reason",
        "(blocked) 2026-13-40: reason",
        "(reopened) 2026-11-20: why",
        "(review) 2026-11-20 by Ada: no verdict",
        "(review) 2026-11-20 maybe: reasons",
        "(review) 2026-11-20 pass 1.2: only changes names items",
        "(review) 2026-11-20 changes one: not a number",
        "(accepted) 2026-11-20 by Ada",
        "(accepted) 2026-11-20 fingerprint xyz by Ada",
        "(accepted) 2026-11-20 fingerprint 81577cca8ff3ca11 1.1 by Ada",
        "(someday) 2026-11-20: unknown kind",
        "(synced) 2026-11-20 fingerprint 0123 by Ada",
    ],
)
def test_one_record_shape_refuses_what_is_not_one(text: str) -> None:
    assert isinstance(parse(text), ParseError)


def test_lines_that_do_not_start_like_a_record_are_not_records() -> None:
    for text in ("Criteria: fifty at most", "(Blocked) 2026-11-20: x", "a (note) in passing", ""):
        assert parse(text) is None
        assert not looks_like_record(text)
    assert looks_like_record("(note) 2026-11-20: x")


def test_every_kind_has_a_shape_that_starts_with_its_name() -> None:
    assert set(KINDS) == set(RecordKind)
    for kind in RecordKind:
        assert shape(kind).startswith(f"({kind.value}) YYYY-MM-DD")


def test_a_kind_with_text_needs_one() -> None:
    with pytest.raises(RecordError):
        render(Record(RecordKind.NOTE, DAY))


def test_who_wrote_a_record(tmp_path: Path) -> None:
    """Requirement "Who wrote a record": --by, else the git user, else nobody."""
    named = tmp_path / "named"
    git_init(named, "Sam Doe")
    unnamed = tmp_path / "unnamed"
    git_init(unnamed, None)
    assert who_for(named, None) == "Sam Doe"
    assert who_for(named, "Ada and Grace") == "Ada and Grace"
    assert who_for(unnamed, None) is None


def test_who_wrote_a_record_refuses_a_name_with_a_colon(tmp_path: Path) -> None:
    git_init(tmp_path, "Sam Doe")
    for name in ("Ada: the planner", "Ada:", "   "):
        with pytest.raises(RecordError):
            who_for(tmp_path, name)


def test_scenario_explicit_author() -> None:
    record = Record(RecordKind.SELF_REVIEW, DAY, who="Ada and Grace", text="<summary>")
    assert render(record) == "(self-review) 2026-11-20 by Ada and Grace: <summary>"


def test_scenario_reviewers_verdict() -> None:
    record = Record(RecordKind.REVIEW, DAY, who="wm-reviewer", verdict=Verdict.PASS, text="ok")
    assert render(record) == "(review) 2026-11-20 pass by wm-reviewer: ok"


def test_a_name_may_hold_the_word_by() -> None:
    record = Record(RecordKind.NOTE, DAY, who="by Ada by Grace", text="x")
    assert parse(render(record)) == record


def test_findings_name_their_place_in_backticks() -> None:
    """Requirement "Findings name their place in backticks"."""
    finding = Finding(ReviewSeverity.WARNING, "src/a.py:12", "the limit is not checked")
    assert render_finding(finding) == "warning `src/a.py:12`: the limit is not checked"
    assert parse_finding(render_finding(finding)) == finding


def test_scenario_place_with_a_line_number() -> None:
    given = parse_finding_argument("warning: src/a.py:12: the limit is not checked")
    assert given == Finding(ReviewSeverity.WARNING, "src/a.py:12", "the limit is not checked")
    assert given is not None
    assert render_finding(given) == "warning `src/a.py:12`: the limit is not checked"


def test_findings_read_a_place_that_holds_a_colon_and_space() -> None:
    finding = Finding(ReviewSeverity.CRITICAL, "docs: getting started", "stale step")
    assert parse_finding(render_finding(finding)) == finding
    given = parse_finding_argument("critical: `docs: getting started`: stale step")
    assert given == finding


def test_findings_refuse_what_is_not_one() -> None:
    assert parse_finding("warning src/a.py: no backticks") is None
    assert parse_finding("major `a.py`: unknown severity") is None
    assert parse_finding_argument("warning: no place") is None
    with pytest.raises(RecordError):
        render_finding(Finding(ReviewSeverity.WARNING, "a`b", "x"))

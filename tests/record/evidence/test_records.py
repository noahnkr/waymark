"""Records: one shape for every line wm writes, read and written in one place."""

import datetime
from pathlib import Path

import pytest

from tests.conftest import git_init
from waymark.record.evidence.records import (
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
    Record(RecordKind.SYNCED, DAY, who="Ada Lovelace"),
    Record(RecordKind.SYNCED, DAY, who="Ada", fingerprint="0123456789abcdef"),
    Record(RecordKind.OVERRIDE, DAY, who="Ada", text="the reviewer is away"),
    Record(RecordKind.SELF_REVIEW, DAY, who="Ada and Grace", text="every scenario holds"),
    Record(RecordKind.REVIEW, DAY, who="reviewer", verdict=Verdict.PASS, text="fine"),
    Record(
        RecordKind.REVIEW,
        DAY,
        who="reviewer",
        verdict=Verdict.CHANGES,
        items=("1.2", "2.1"),
        text="the limit is not checked",
    ),
    Record(RecordKind.REVIEW, DAY, verdict=Verdict.SPEC_GAP, text="the limit is unspecified"),
    Record(
        RecordKind.SELF_REVIEW, DAY, who="Ada", text="every scenario holds", covers=("1.1", "1.2")
    ),
    Record(
        RecordKind.REVIEW,
        DAY,
        who="reviewer",
        verdict=Verdict.PASS,
        text="the added item holds",
        covers=("1.3",),
    ),
    Record(
        RecordKind.REVIEW,
        DAY,
        verdict=Verdict.CHANGES,
        items=("1.3",),
        text="off by one",
        covers=("1.3",),
    ),
    Record(RecordKind.RESOLVED, DAY, who="Ada", text="use the test key: it is enough"),
    Record(RecordKind.REOPENED, DAY, who="Ada Lovelace"),
    Record(RecordKind.REOPENED, DAY),
    Record(
        RecordKind.REOPENED, DAY, who="planner for Ada", item="1.2", text="its criteria changed"
    ),
    Record(RecordKind.BLOCKED, DAY, who="Ada", text="the API key is missing"),
    Record(RecordKind.GAP, DAY, text="the limit's maximum"),
    Record(RecordKind.NOTE, DAY, who="implementer", text="partial: the parser is done"),
    Record(RecordKind.TICKED, DAY, who="planner for Ada", item="1.1"),
    Record(RecordKind.TICKED, DAY, who="Ada", item="1.2"),
    Record(RecordKind.REVISED, DAY, who="planner for Ada", text="the count was 2", parts=("2.2",)),
    Record(
        RecordKind.REVISED,
        DAY,
        who="planner for Ada",
        text="settled the cut",
        parts=("proposal", "design", "specs/search", "1.3"),
    ),
    Record(RecordKind.REVISED, DAY, text="reworded the why"),
    Record(RecordKind.ARCHIVED, DAY, who="Ada"),
    Record(RecordKind.ARCHIVED, DAY, who="Ada", change="add-limit"),
]


@pytest.mark.parametrize(
    "line",
    [
        "2026-11-16 (note) 1.2 by wm-implementer: partial: the parser is done",
        "2026-11-16 (review) pass covers 1.1, 1.2 by wm-reviewer: fine",
        "2026-11-16 (note) 1.2 by Noah Roberts: written by the planner before the rule",
    ],
)
def test_records_written_under_the_old_names_are_read_as_they_are(line: str) -> None:
    """Requirement "Who wrote a record": records already written keep who they name."""
    found = parse(line)
    assert isinstance(found, Record)
    assert render(found) == line
    assert found.who == line.split(" by ", 1)[1].split(":", 1)[0]


def test_new_kinds_have_their_shapes() -> None:
    rendered = {render(record) for record in ONE_OF_EACH}
    assert {
        "2026-11-20 (ticked) 1.1 by planner for Ada",
        "2026-11-20 (revised) 2.2 by planner for Ada: the count was 2",
        "2026-11-20 (revised) proposal, design, specs/search, 1.3 by planner for Ada: "
        "settled the cut",
        "2026-11-20 (revised): reworded the why",
        "2026-11-20 (archived) by Ada",
        "2026-11-20 (archived) add-limit by Ada",
    } <= rendered


@pytest.mark.parametrize(
    "text",
    [
        "2026-11-20 (ticked) by Ada: done",
        "2026-11-20 (ticked) 1.1 1.2 by Ada",
        "2026-11-20 (revised) 2.2 3.1 by Ada: two parts without a comma",
        "2026-11-20 (revised) tests by Ada: not a part",
        "2026-11-20 (revised) by Ada",
        "2026-11-20 (archived) add-limit extra by Ada",
    ],
)
def test_a_malformed_new_record_names_its_shape(text: str) -> None:
    found = parse(text)
    assert isinstance(found, ParseError)
    assert found.kind is not None
    assert shape(found.kind) in found.message


@pytest.mark.parametrize("record", ONE_OF_EACH, ids=render)
def test_one_record_shape(record: Record) -> None:
    """Requirement "One record shape": every kind renders and reads back the same."""
    assert parse(render(record)) == record


def test_one_record_shape_puts_the_arguments_before_who_wrote_it() -> None:
    rendered = {render(record) for record in ONE_OF_EACH}
    assert {
        "2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 items 1.1, 1.2 by Ada Lovelace",
        "2026-11-20 (review) changes 1.2, 2.1 by reviewer: the limit is not checked",
        "2026-11-20 (review) pass covers 1.3 by reviewer: the added item holds",
        "2026-11-20 (review) changes 1.3; covers 1.3: off by one",
        "2026-11-20 (self-review) covers 1.1, 1.2 by Ada: every scenario holds",
        "2026-11-20 (reopened) by Ada Lovelace",
        "2026-11-20 (reopened)",
        "2026-11-20 (blocked) by Ada: the API key is missing",
    } <= rendered


def test_scenario_record_in_its_shape() -> None:
    """Requirement "One record shape": the kind, its item, who wrote it, then the text."""
    record = Record(
        RecordKind.BLOCKED, DAY, who="planner for Ada", text="the API key is missing", item="1.2"
    )
    line = render(record)
    assert line == "2026-11-20 (blocked) 1.2 by planner for Ada: the API key is missing"
    assert parse(line) == record


def test_scenario_malformed_record() -> None:
    found = parse("(blocked) 1.2 the API key is missing")
    assert isinstance(found, ParseError)
    assert found.kind is RecordKind.BLOCKED
    assert "YYYY-MM-DD (blocked) <item> [by <who>]: <reason>" in found.message


@pytest.mark.parametrize(
    "text",
    [
        "2026-11-20 (blocked)",
        "2026-11-20 (blocked) by Ada",
        "2026-11-20 (blocked) by : reason",
        "2026-11-20 (blocked) soon: reason",
        "2026-11-20 (blocked):reason",
        "2026-13-40 (blocked): reason",
        "2026-11-20 (review) by Ada: no verdict",
        "2026-11-20 (review) maybe: reasons",
        "2026-11-20 (review) pass 1.2: only changes names items",
        "2026-11-20 (review) changes one: not a number",
        "2026-11-20 (accepted) by Ada",
        "2026-11-20 (accepted) fingerprint xyz by Ada",
        "2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 1.1 by Ada",
        "2026-11-20 (accepted) fingerprint 81577cca8ff3ca11 by Ada",
        "(someday) 2026-11-20: unknown kind",
        "2026-11-20 (synced) fingerprint 0123 by Ada",
        "2026-11-20 (review) pass covers by Ada: no items",
        "2026-11-20 (review) pass covers one: not a number",
        "2026-11-20 (review) covers 1.1 pass: covers before the verdict",
        "2026-11-20 (self-review) covers: no items",
        "2026-11-20 (self-review) covers 1.1 two: not a number",
        "2026-11-20 (self-review) 1.1 by Ada: no covers word",
    ],
)
def test_one_record_shape_refuses_what_is_not_one(text: str) -> None:
    assert isinstance(parse(text), ParseError)


def test_lines_that_do_not_start_like_a_record_are_not_records() -> None:
    for text in (
        "**Criteria:** fifty at most",
        "(Blocked) 2026-11-20: x",
        "a (note) in passing",
        "",
    ):
        assert parse(text) is None
        assert not looks_like_record(text)
    assert looks_like_record("2026-11-20 (note): x")


def test_every_kind_has_a_shape_that_starts_with_the_date_and_its_name() -> None:
    assert set(KINDS) == set(RecordKind)
    for kind in RecordKind:
        assert shape(kind).startswith(f"YYYY-MM-DD ({kind.value})")


def test_a_kind_with_text_needs_one() -> None:
    with pytest.raises(RecordError):
        render(Record(RecordKind.NOTE, DAY))


def test_who_wrote_a_record(tmp_path: Path) -> None:
    """Requirement "Who wrote a record": --by, else whoever the record's kind names."""
    named = tmp_path / "named"
    git_init(named, "Sam Doe")
    unnamed = tmp_path / "unnamed"
    git_init(unnamed, None)
    for kind in (
        RecordKind.ACCEPTED,
        RecordKind.OVERRIDE,
        RecordKind.RESOLVED,
        RecordKind.ARCHIVED,
    ):
        assert who_for(named, kind, None) == "Sam Doe"
        assert who_for(unnamed, kind, None) is None
    for kind in (
        RecordKind.NOTE,
        RecordKind.BLOCKED,
        RecordKind.GAP,
        RecordKind.REOPENED,
        RecordKind.SELF_REVIEW,
        RecordKind.SYNCED,
        RecordKind.REVISED,
        RecordKind.ADDED,
        RecordKind.DROPPED,
        RecordKind.MOVED,
        RecordKind.PROPOSED,
    ):
        assert who_for(named, kind, None) == "planner for Sam Doe"
        assert who_for(unnamed, kind, None) == "planner"
    assert who_for(named, RecordKind.TICKED, None) == "planner for Sam Doe"
    assert who_for(named, RecordKind.TICKED, None, human=True) == "Sam Doe"
    assert who_for(named, RecordKind.NOTE, "Ada and Grace") == "Ada and Grace"


def test_who_wrote_a_record_refuses_a_name_with_a_colon(tmp_path: Path) -> None:
    git_init(tmp_path, "Sam Doe")
    for name in ("Ada: the planner", "Ada:", "   "):
        with pytest.raises(RecordError):
            who_for(tmp_path, RecordKind.NOTE, name)


def test_scenario_explicit_author() -> None:
    record = Record(
        RecordKind.SELF_REVIEW, DAY, who="Ada and Grace", text="<summary>", covers=("1.1", "1.2")
    )
    assert render(record) == "2026-11-20 (self-review) covers 1.1, 1.2 by Ada and Grace: <summary>"


def test_scenario_reviewers_verdict() -> None:
    record = Record(
        RecordKind.REVIEW,
        DAY,
        who="reviewer",
        verdict=Verdict.PASS,
        text="<reasons>",
        covers=("1.1", "1.2"),
    )
    assert render(record) == "2026-11-20 (review) pass covers 1.1, 1.2 by reviewer: <reasons>"


def test_a_review_without_covers_reads_as_covering_every_item() -> None:
    found = parse("2026-11-20 (review) pass by reviewer: written before covers")
    assert isinstance(found, Record)
    assert found.covers is None


def test_a_name_may_hold_the_word_by() -> None:
    record = Record(RecordKind.NOTE, DAY, who="by Ada by Grace", text="x")
    assert parse(render(record)) == record


def test_findings_name_their_place_in_backticks() -> None:
    """Requirement "Findings name their place in backticks"."""
    finding = Finding(ReviewSeverity.WARNING, "src/a.py:12", "the limit is not checked")
    assert render_finding(finding) == "[warning] `src/a.py:12`: the limit is not checked"
    assert parse_finding(render_finding(finding)) == finding


def test_scenario_place_with_a_line_number() -> None:
    given = parse_finding_argument("warning: src/a.py:12: the limit is not checked")
    assert given == Finding(ReviewSeverity.WARNING, "src/a.py:12", "the limit is not checked")
    assert given is not None
    assert render_finding(given) == "[warning] `src/a.py:12`: the limit is not checked"


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


MILESTONE_RECORDS = [
    Record(RecordKind.ADDED, DAY, who="Ada", text="cache hot queries", change="add-cache"),
    Record(RecordKind.DROPPED, DAY, who="Ada", text="fast enough", change="add-cache"),
    Record(RecordKind.MOVED, DAY, who="Ada", change="add-cache", after="add-index"),
    Record(RecordKind.MOVED, DAY, change="add-cache"),
    Record(RecordKind.PROPOSED, DAY, who="Ada Lovelace", change="add-cache"),
    Record(RecordKind.ARCHIVED, DAY, change="add-cache"),
]


@pytest.mark.parametrize("record", MILESTONE_RECORDS, ids=render)
def test_milestone_records_read_back_the_same(record: Record) -> None:
    """Requirement "Milestone log": each kind renders and reads back the same."""
    assert parse(render(record)) == record


def test_milestone_records_have_the_shapes_of_the_milestone_log() -> None:
    assert [render(record) for record in MILESTONE_RECORDS] == [
        "2026-11-20 (added) add-cache by Ada: cache hot queries",
        "2026-11-20 (dropped) add-cache by Ada: fast enough",
        "2026-11-20 (moved) add-cache after add-index by Ada",
        "2026-11-20 (moved) add-cache first",
        "2026-11-20 (proposed) add-cache by Ada Lovelace",
        "2026-11-20 (archived) add-cache",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "2026-11-20 (added) by Ada: no change named",
        "2026-11-20 (added) add-cache by Ada",
        "2026-11-20 (added) Add_Cache: not a name",
        "2026-11-20 (proposed) add-cache extra by Ada",
        "2026-11-20 (proposed) add-cache: no text",
        "2026-11-20 (moved) add-cache by Ada",
        "2026-11-20 (moved) add-cache after by Ada",
        "2026-11-20 (moved) add-cache before add-index",
    ],
)
def test_malformed_milestone_records_are_refused(text: str) -> None:
    assert isinstance(parse(text), ParseError)


def test_a_record_is_written_date_first_with_comma_separated_items() -> None:
    """Requirement "Record shape": the date first, item lists with commas, `;` before covers."""
    review = Record(
        RecordKind.REVIEW,
        datetime.date(2026, 11, 20),
        who="reviewer",
        text="off by one",
        verdict=Verdict.CHANGES,
        items=("1.2", "2.2"),
        covers=("1.1", "1.2", "2.2"),
    )
    line = render(review)
    assert line == (
        "2026-11-20 (review) changes 1.2, 2.2; covers 1.1, 1.2, 2.2 by reviewer: off by one"
    )
    assert parse(line) == review
    passed = Record(
        RecordKind.REVIEW,
        datetime.date(2026, 11, 20),
        who="reviewer",
        text="fine",
        verdict=Verdict.PASS,
        covers=("1.1", "1.2"),
    )
    assert render(passed) == "2026-11-20 (review) pass covers 1.1, 1.2 by reviewer: fine"
    accepted = Record(
        RecordKind.ACCEPTED,
        datetime.date(2026, 11, 20),
        who="Ada",
        fingerprint="0123456789abcdef",
        items=("1.1", "1.2"),
    )
    line = render(accepted)
    assert line == "2026-11-20 (accepted) fingerprint 0123456789abcdef items 1.1, 1.2 by Ada"
    assert parse(line) == accepted


def test_scenario_kind_before_the_date() -> None:
    """The older shape starts like a record, so it is reported, never read."""
    found = parse("(blocked) 2026-11-20 1.2 by Ada: the API key is missing")
    assert isinstance(found, ParseError)
    assert "YYYY-MM-DD (blocked) <item> [by <who>]: <reason>" in found.message
    assert looks_like_record("(note) 2026-11-20: text")
    assert looks_like_record("2026-11-20 (note): text")
    note = parse("2026-11-20 (note): text")
    assert isinstance(note, Record)
    assert (note.kind, note.text, note.who) == (RecordKind.NOTE, "text", None)
    reopened = parse("2026-11-20 (reopened)")
    assert isinstance(reopened, Record)


def test_a_name_with_a_comma_is_kept_whole() -> None:
    record = parse("2026-11-20 (accepted) fingerprint 0123456789abcdef items 1.1 by Doe, Sam")
    assert isinstance(record, Record)
    assert (record.items, record.who) == (("1.1",), "Doe, Sam")


def test_a_finding_is_written_with_its_severity_in_brackets() -> None:
    finding = Finding(ReviewSeverity.CRITICAL, "src/a.py:12", "the limit is not checked")
    assert render_finding(finding) == "[critical] `src/a.py:12`: the limit is not checked"
    assert parse_finding("[critical] `src/a.py:12`: the limit is not checked") == finding


def test_scenario_item_list_without_commas() -> None:
    for line in (
        "2026-11-20 (accepted) fingerprint 0123456789abcdef items 1.1 1.2 by Ada",
        "2026-11-20 (review) changes 1.2, 2.2 covers 1.1, 1.2 by reviewer: off",
        "2026-11-20 (review) changes 1.2; by reviewer: off",
        "2026-11-20 (self-review) covers 1.1,1.2 by Ada: fine",
    ):
        found = parse(line)
        assert isinstance(found, ParseError), line
    found = parse("2026-11-20 (accepted) fingerprint 0123456789abcdef items 1.1 1.2 by Ada")
    assert isinstance(found, ParseError)
    assert "YYYY-MM-DD (accepted) fingerprint <digest> items <item>, <item>... [by <who>]" in (
        found.message
    )


def test_a_bare_severity_is_not_a_finding() -> None:
    assert parse_finding("critical `src/a.py:12`: the limit is not checked") is None


@pytest.mark.parametrize(
    "kind", [RecordKind.BLOCKED, RecordKind.GAP, RecordKind.NOTE, RecordKind.RESOLVED]
)
def test_an_item_record_names_its_item_after_the_kind(kind: RecordKind) -> None:
    record = Record(kind, DAY, who="Ada", text="the key", item="1.2")
    assert render(record) == f"2026-11-20 ({kind.value}) 1.2 by Ada: the key"
    assert parse(render(record)) == record


def test_a_reopened_record_names_its_item() -> None:
    record = Record(RecordKind.REOPENED, DAY, who="Ada", item="1.2")
    assert render(record) == "2026-11-20 (reopened) 1.2 by Ada"
    assert parse("2026-11-20 (reopened) 1.2 by Ada") == record


def test_a_resolved_record_may_name_no_item() -> None:
    found = parse("2026-11-20 (resolved) by Sam: fifty")
    assert isinstance(found, Record)
    assert found.item is None


def test_an_item_record_names_one_item_number() -> None:
    for text in ("2026-11-20 (note) 1.2 2.1: x", "2026-11-20 (note) soon: x"):
        found = parse(text)
        assert isinstance(found, ParseError)
        assert "one item number" in found.message

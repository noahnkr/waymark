"""Deltas: parsing them and merging them into specs."""

from tests.support import delta, document, requirement, spec
from waymark.record.artifacts.deltas import Delta, Merge, delta_is_merged, merge_delta, parse_delta
from waymark.record.artifacts.specs import Spec, parse_spec

LIMIT = requirement()
EMPTY = requirement("Empty query", "An empty query SHALL be refused.", "No words")
ORDER = requirement("Result order", "Results SHALL be sorted by date.", "Two matches")
LIMIT_CHANGED = requirement(statement="A search SHALL return at most twenty results.")


def parse(text: str) -> Delta:
    return parse_delta("search", document(text, "changes/add-limit/specs/search.md"))


def living(text: str) -> Spec:
    return parse_spec("search", document(text, "specs/search.md"))


def merge(spec_text: str | None, delta_text: str) -> Merge:
    return merge_delta(living(spec_text) if spec_text is not None else None, parse(delta_text))


def merged(spec_text: str | None, delta_text: str) -> str:
    result = merge(spec_text, delta_text)
    assert result.problems == ()
    assert result.text is not None
    return result.text


def codes(result: Merge) -> list[str]:
    assert result.text is None
    return [problem.code for problem in result.problems]


def test_delta_has_added_modified_and_removed_requirements() -> None:
    parsed = parse(
        delta(added=(EMPTY,), modified=(LIMIT_CHANGED,), removed=(("Result order", "Unused."),))
    )
    assert parsed.problems == ()
    assert [item.name for item in parsed.added] == ["Empty query"]
    assert [item.name for item in parsed.modified] == ["Result limit"]
    assert [(item.name, item.reason) for item in parsed.removed] == [("Result order", "Unused.")]


def test_removed_requirement_gives_a_reason() -> None:
    text = delta(removed=(("Result order", "Unused."),)).replace("**Reason:** Unused.\n", "")
    assert [problem.code for problem in parse(text).problems] == ["removal-without-reason"]


def test_delta_that_changes_nothing_is_a_problem() -> None:
    assert [problem.code for problem in parse("# Search\n").problems] == ["empty-delta"]


def test_delta_names_a_requirement_in_one_operation_only() -> None:
    parsed = parse(delta(added=(LIMIT,), removed=(("Result limit", "Replaced."),)))
    assert [problem.code for problem in parsed.problems] == ["duplicate-requirement"]


def test_delta_rejects_unknown_sections() -> None:
    parsed = parse(delta(added=(LIMIT,)) + "\n## Notes on requirements\n")
    assert [problem.code for problem in parsed.problems] == ["unknown-section"]


def test_delta_requirements_follow_the_spec_format() -> None:
    parsed = parse(delta(added=("### Requirement: Result limit\nSearch stops at fifty.\n",)))
    assert {problem.code for problem in parsed.problems} == {
        "requirement-without-shall",
        "requirement-without-scenario",
    }


def test_merge_added_requirement_is_appended_to_the_spec() -> None:
    result = living(merged(spec(LIMIT), delta(added=(EMPTY,))))
    assert result.problems == ()
    assert [item.name for item in result.requirements] == ["Result limit", "Empty query"]


def test_merge_modified_requirement_replaces_the_one_with_the_same_heading() -> None:
    result = living(merged(spec(LIMIT, EMPTY), delta(modified=(LIMIT_CHANGED,))))
    assert [item.name for item in result.requirements] == ["Result limit", "Empty query"]
    assert result.requirements[0].statement == "A search SHALL return at most twenty results."


def test_merge_removed_requirement_is_deleted_from_the_spec() -> None:
    text = merged(
        spec(LIMIT, EMPTY, ORDER), delta(removed=(("Empty query", "Covered elsewhere."),))
    )
    assert [item.name for item in living(text).requirements] == ["Result limit", "Result order"]
    assert "Empty query" not in text


def test_merge_removing_the_last_requirement_leaves_a_tidy_spec() -> None:
    text = merged(spec(LIMIT, EMPTY), delta(removed=(("Empty query", "Covered elsewhere."),)))
    assert text == spec(LIMIT)


def test_merge_added_requirement_creates_a_spec_that_does_not_exist() -> None:
    text = merged(None, delta(added=(LIMIT, EMPTY), purpose="How search behaves."))
    created = living(text)
    assert created.problems == ()
    assert created.title == "Search"
    assert created.purpose == "How search behaves."
    assert [item.name for item in created.requirements] == ["Result limit", "Empty query"]


def test_merge_creating_a_spec_needs_a_purpose() -> None:
    assert codes(merge(None, delta(added=(LIMIT,)))) == ["delta-without-purpose"]


def test_merge_rename_is_a_removal_plus_an_addition() -> None:
    renamed = requirement("Result cap")
    text = merged(
        spec(LIMIT, EMPTY), delta(added=(renamed,), removed=(("Result limit", "Renamed."),))
    )
    assert [item.name for item in living(text).requirements] == ["Empty query", "Result cap"]


def test_merge_applies_all_three_operations_at_once() -> None:
    text = merged(
        spec(LIMIT, EMPTY),
        delta(added=(ORDER,), modified=(LIMIT_CHANGED,), removed=(("Empty query", "Dropped."),)),
    )
    result = living(text)
    assert result.problems == ()
    assert [item.name for item in result.requirements] == ["Result limit", "Result order"]
    assert "twenty" in result.requirements[0].statement


def test_merge_modified_requirement_missing_from_the_spec_is_a_mismatch() -> None:
    assert codes(merge(spec(EMPTY), delta(modified=(LIMIT_CHANGED,)))) == [
        "delta-requirement-missing"
    ]


def test_merge_removed_requirement_missing_from_the_spec_is_a_mismatch() -> None:
    assert codes(merge(spec(EMPTY), delta(removed=(("Result limit", "Gone."),)))) == [
        "delta-requirement-missing"
    ]


def test_merge_added_requirement_already_in_the_spec_is_a_mismatch() -> None:
    assert codes(merge(spec(LIMIT), delta(added=(LIMIT_CHANGED,)))) == ["delta-requirement-exists"]


def test_merge_modifying_a_spec_that_does_not_exist_is_a_mismatch() -> None:
    result = merge(None, delta(modified=(LIMIT_CHANGED,), purpose="How search behaves."))
    assert codes(result) == ["delta-requirement-missing"]


def test_merge_refuses_a_delta_with_format_problems() -> None:
    assert codes(merge(spec(LIMIT), "# Search\n")) == ["empty-delta"]


def test_merge_refuses_a_spec_with_format_problems() -> None:
    broken = spec(LIMIT) + "\n## Notes\n"
    assert codes(merge(broken, delta(added=(EMPTY,)))) == ["spec-unreadable"]


def test_merge_leaves_every_other_line_of_the_spec_unchanged() -> None:
    odd = spec(LIMIT, EMPTY, ORDER).replace("How search behaves.", "How  search   behaves.  ")
    odd = odd.replace("### Requirement: Result order", "\n\n### Requirement: Result order")
    text = merged(odd, delta(modified=(LIMIT_CHANGED,)))
    before = odd.split("\n")
    after = text.split("\n")
    assert len(before) == len(after)
    changed = [
        index for index, pair in enumerate(zip(before, after, strict=True)) if pair[0] != pair[1]
    ]
    assert [before[index] for index in changed] == ["A search SHALL return at most fifty results."]


def test_merge_keeps_the_specs_line_endings() -> None:
    windows = spec(LIMIT).replace("\n", "\r\n")
    text = merged(windows, delta(added=(EMPTY,), modified=(LIMIT_CHANGED,)))
    assert "\r\n" in text
    assert "\n" not in text.replace("\r\n", "")


def test_merge_new_spec_takes_the_deltas_line_endings() -> None:
    windows = delta(added=(LIMIT,), purpose="How search behaves.").replace("\n", "\r\n")
    text = merged(None, windows)
    assert "\n" not in text.replace("\r\n", "")
    assert living(text).problems == ()


def test_merge_can_replace_the_purpose_and_the_repos() -> None:
    text = merged(spec(LIMIT), delta(purpose="Everything about search.", repos="api, web"))
    result = living(text)
    assert result.problems == ()
    assert result.purpose == "Everything about search."
    assert result.repos == ("api", "web")
    again = living(merged(text, delta(repos="api")))
    assert again.repos == ("api",)
    assert again.purpose == "Everything about search."


def test_merge_into_a_spec_without_a_final_newline() -> None:
    text = merged(spec(LIMIT).rstrip("\n"), delta(added=(EMPTY,)))
    assert text.endswith("- THEN the limit holds\n")
    assert [item.name for item in living(text).requirements] == ["Result limit", "Empty query"]


def test_merge_is_deterministic() -> None:
    change = delta(added=(ORDER,), modified=(LIMIT_CHANGED,))
    assert merged(spec(LIMIT, EMPTY), change) == merged(spec(LIMIT, EMPTY), change)


CAP = requirement("Result cap")
RENAME = "# Search\n\n## RENAMED Requirements\n\n- **From:** Result cap\n- **To:** Result limit\n"


def test_delta_sections_take_the_new_headings() -> None:
    """Requirement "Delta sections": the upper-case headings read like the old ones."""
    text = (
        delta(added=(LIMIT,)).replace("## ADDED Requirements", "## ADDED Requirements")
        + "\n## REMOVED Requirements\n\n### Requirement: Old\n**Reason:** gone\n"
    )
    parsed = parse(text)
    assert parsed.problems == ()
    assert [r.name for r in parsed.added] == ["Result limit"]
    assert [r.name for r in parsed.removed] == ["Old"]


def test_scenario_requirement_renamed() -> None:
    spec_text = spec(CAP, requirement("Empty query"))
    text = merged(spec_text, RENAME)
    renamed = living(text)
    assert [r.name for r in renamed.requirements] == ["Result limit", "Empty query"]
    before = living(spec_text).requirement("Result cap")
    after = renamed.requirement("Result limit")
    assert before is not None
    assert after is not None
    assert after.block[1:] == before.block[1:]
    assert renamed.requirement("Result cap") is None


def test_rename_matches_the_heading_in_any_case_or_spacing() -> None:
    """Requirement "Delta sections": the heading is rebuilt, not edited in place."""
    spec_text = spec(requirement("result   CAP"))
    renamed = living(merged(spec_text, RENAME))
    assert [r.name for r in renamed.requirements] == ["Result limit"]
    assert "### Requirement: Result limit\n" in merged(spec_text, RENAME)


def test_rename_of_a_name_inside_the_heading_prefix() -> None:
    text = "# Search\n\n## RENAMED Requirements\n\n- **From:** Re\n- **To:** Query\n"
    renamed = living(merged(spec(requirement("Re")), text))
    assert [r.name for r in renamed.requirements] == ["Query"]


def test_a_rename_and_a_modification_in_one_delta() -> None:
    text = RENAME + "\n## MODIFIED Requirements\n\n" + LIMIT_CHANGED
    renamed = living(merged(spec(CAP), text))
    limit = renamed.requirement("Result limit")
    assert limit is not None
    assert "twenty" in limit.statement


def test_scenario_rename_of_a_missing_requirement() -> None:
    assert codes(merge(spec(LIMIT), RENAME.replace("Result limit", "Result size"))) == [
        "delta-requirement-missing"
    ]
    assert codes(merge(spec(CAP, LIMIT), RENAME)) == ["delta-requirement-exists"]


def test_renames_are_pairs() -> None:
    assert [p.code for p in parse(RENAME + "- **From:** Lonely\n").problems] == ["malformed-rename"]
    assert [p.code for p in parse(RENAME.replace("- **From:** Result cap\n", "")).problems] == [
        "malformed-rename",
        "empty-delta",
    ]
    parsed = parse(RENAME)
    assert [(r.old, r.new) for r in parsed.renamed] == [("Result cap", "Result limit")]
    assert ("result cap", "Result cap") in parsed.touched()


APFM = "Leads come from A Place for Mom."
BOTH = "Leads come from A Place for Mom and Caring.com."


def with_background(spec_text: str, background: str) -> str:
    return spec_text.replace("## Requirements", f"## Background\n\n{background}\n\n## Requirements")


def background_delta(background: str) -> str:
    return f"# Search\n\n## Background\n\n{background}\n"


def test_scenario_background_set_by_a_delta() -> None:
    """Requirement "Spec background": the section goes in after the Purpose."""
    before = spec(LIMIT, EMPTY)
    text = merged(before, background_delta(APFM))
    result = living(text)
    assert result.problems == ()
    assert result.background == APFM
    assert text == with_background(before, APFM)
    assert [r.block for r in result.requirements] == [r.block for r in living(before).requirements]


def test_scenario_background_replaced() -> None:
    before = with_background(spec(LIMIT), APFM)
    text = merged(before, background_delta(BOTH))
    assert living(text).background == BOTH
    assert text == with_background(spec(LIMIT), BOTH)


def test_a_new_spec_takes_the_background_after_its_purpose() -> None:
    text = merged(
        None,
        delta(purpose="How search behaves.", added=(LIMIT,)).replace(
            "## ADDED", f"## Background\n\n{APFM}\n\n## ADDED"
        ),
    )
    assert text == with_background(spec(LIMIT), APFM)


def test_a_background_already_set_is_merged() -> None:
    """A sync re-run writes nothing once the spec holds the delta's Background."""
    target = living(with_background(spec(LIMIT), APFM))
    assert delta_is_merged(target, parse(background_delta(APFM)))
    assert not delta_is_merged(target, parse(background_delta(BOTH)))
    assert not delta_is_merged(living(spec(LIMIT)), parse(background_delta(APFM)))


def test_scenario_empty_background() -> None:
    empty = "# Search\n\n## Background\n\n## ADDED Requirements\n\n" + EMPTY
    problems = parse(empty).problems
    assert [(p.code, p.line) for p in problems] == [("empty-section", 3)]
    assert "Background" in problems[0].message
    assert "empty" in problems[0].message
    spec_problems = living(with_background(spec(LIMIT), "")).problems
    assert [(p.code, p.line) for p in spec_problems] == [("empty-section", 7)]


def test_a_spec_may_have_a_background() -> None:
    result = living(with_background(spec(LIMIT), APFM))
    assert result.problems == ()
    assert result.background == APFM
    assert living(spec(LIMIT)).background is None

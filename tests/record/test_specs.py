"""Living specs: requirements and scenarios."""

from tests.support import document, requirement, spec
from waymark.record.specs import Spec, parse_spec, requirement_key


def parse(text: str) -> Spec:
    return parse_spec("search", document(text, "specs/search.md"))


def codes(text: str) -> list[str]:
    return [problem.code for problem in parse(text).problems]


def test_spec_has_a_title_a_purpose_and_requirements() -> None:
    parsed = parse(spec(requirement(), requirement("Empty query", "An empty query SHALL fail.")))
    assert parsed.problems == ()
    assert parsed.title == "Search"
    assert parsed.purpose == "How search behaves."
    assert [item.name for item in parsed.requirements] == ["Result limit", "Empty query"]


def test_requirement_has_a_statement_and_scenarios_with_steps() -> None:
    (parsed,) = parse(spec()).requirements
    assert parsed.statement == "A search SHALL return at most fifty results."
    (scenario,) = parsed.scenarios
    assert scenario.name == "Many matches"
    assert [keyword for keyword, _ in scenario.steps] == ["GIVEN", "WHEN", "THEN"]
    assert scenario.steps[2] == ("THEN", "the limit holds")


def test_requirement_block_runs_from_its_heading_to_its_last_line() -> None:
    first, second = parse(spec(requirement(), requirement("Empty query"))).requirements
    assert first.block[0] == "### Requirement: Result limit"
    assert first.block[-1] == "- THEN the limit holds"
    assert first.extent_end == second.start


def test_requirement_without_a_scenario_is_a_problem() -> None:
    text = spec("### Requirement: Result limit\nA search SHALL return at most fifty results.\n")
    assert codes(text) == ["requirement-without-scenario"]


def test_requirement_without_shall_is_a_problem() -> None:
    assert codes(spec(requirement(statement="A search returns fifty results."))) == [
        "requirement-without-shall"
    ]


def test_requirement_heading_is_unique_within_a_spec() -> None:
    assert codes(spec(requirement(), requirement("result  LIMIT"))) == ["duplicate-requirement"]


def test_requirement_key_ignores_case_and_spacing() -> None:
    assert requirement_key("Result  limit ") == requirement_key("result LIMIT")
    assert parse(spec()).requirement("RESULT limit") is not None


def test_scenario_needs_a_when_and_a_then() -> None:
    text = spec(requirement()).replace("- WHEN a search runs\n", "")
    assert codes(text) == ["scenario-incomplete"]


def test_scenario_line_that_is_not_a_step_is_a_problem() -> None:
    text = spec(requirement()).replace("- WHEN a search runs", "The search runs.")
    assert codes(text) == ["scenario-format", "scenario-incomplete"]


def test_heading_under_requirements_must_name_a_requirement() -> None:
    assert codes(spec("### Result limit\nA search SHALL stop at fifty.\n")) == [
        "requirement-format"
    ]


def test_text_outside_a_requirement_is_a_problem() -> None:
    text = spec(requirement()).replace("## Requirements\n", "## Requirements\n\nStray text.\n")
    assert codes(text) == ["unexpected-text"]


def test_spec_sections_are_purpose_and_requirements_only() -> None:
    assert codes(spec() + "\n## Notes\n\nExtra.\n") == ["unknown-section"]
    assert codes("# Search\n\n## Requirements\n") == ["missing-section"]


def test_spec_can_say_which_repos_it_covers() -> None:
    parsed = parse(spec().replace("# Search\n", "# Search\n\nRepos: api, web\n"))
    assert parsed.problems == ()
    assert parsed.repos == ("api", "web")


def test_requirement_inside_a_code_fence_is_not_a_requirement() -> None:
    fenced = requirement().replace(
        "#### Scenario", "```\n### Requirement: Not real\n```\n\n#### Scenario"
    )
    parsed = parse(spec(fenced))
    assert [item.name for item in parsed.requirements] == ["Result limit"]

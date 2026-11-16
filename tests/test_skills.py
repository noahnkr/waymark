"""The shipped skills: one layout for every skill (requirement "Skill layout")."""

import pytest

from waymark import assets

FIRST = ("Role", "Inputs", "Steps")
LAST = ("Quality bar", "Show the human", "When to stop", "Rules")
SHARED_LINE = "- The shared rules from `wm instructions` apply"


def headings(text: str) -> list[str]:
    """The skill's `##` headings in order, outside fenced code."""
    found: list[str] = []
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            found.append(line[3:].strip())
    return found


def layout_problems(name: str, text: str) -> list[str]:
    """What breaks the layout, each naming the skill and the heading out of place."""
    found = headings(text)
    problems: list[str] = []
    for position, wanted in enumerate(FIRST):
        got = found[position] if position < len(found) else None
        if got != wanted:
            problems.append(
                f'{name}: "## {wanted}" should be heading {position + 1}, found {got!r}'
            )
    for offset, wanted in enumerate(LAST):
        position = len(found) - len(LAST) + offset
        got = found[position] if 0 <= position < len(found) else None
        if got != wanted:
            problems.append(
                f'{name}: "## {wanted}" should come {offset + 1} of the last four, found {got!r}'
            )
    for heading in found[len(FIRST) : len(found) - len(LAST)]:
        if heading in FIRST + LAST:
            problems.append(f'{name}: "## {heading}" is out of place')
    _, _, rules = text.partition("\n## Rules\n")
    first_bullet = next((line for line in rules.split("\n") if line.startswith("- ")), "")
    if not first_bullet.startswith(SHARED_LINE):
        problems.append(f"{name}: the first rule should point at the shared rules")
    return problems


@pytest.mark.parametrize("name", assets.SKILLS)
def test_scenario_installed_skills(name: str) -> None:
    assert layout_problems(name, assets.skill(name)) == []


def test_scenario_a_section_out_of_place() -> None:
    text = assets.skill("wm-fix")
    quality = text.index("## Quality bar")
    stop = text.index("## When to stop")
    rules = text.index("## Rules")
    swapped = text[:quality] + text[stop:rules] + text[quality:stop] + text[rules:]
    problems = layout_problems("wm-fix", swapped)
    assert problems
    assert all(problem.startswith("wm-fix: ") for problem in problems)
    assert any('"## When to stop"' in problem for problem in problems)


def test_a_skill_may_add_its_own_sections_between_steps_and_quality_bar() -> None:
    assert "The loop" in headings(assets.skill("wm-apply"))
    assert layout_problems("wm-apply", assets.skill("wm-apply")) == []


def test_a_missing_shared_rules_line_is_reported() -> None:
    text = assets.skill("wm-pr").replace(SHARED_LINE, "- Something else")
    assert layout_problems("wm-pr", text) == [
        "wm-pr: the first rule should point at the shared rules"
    ]

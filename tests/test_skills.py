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
    text = assets.skill("wm-pr")
    quality = text.index("## Quality bar")
    stop = text.index("## When to stop")
    rules = text.index("## Rules")
    swapped = text[:quality] + text[stop:rules] + text[quality:stop] + text[rules:]
    problems = layout_problems("wm-pr", swapped)
    assert problems
    assert all(problem.startswith("wm-pr: ") for problem in problems)
    assert any('"## When to stop"' in problem for problem in problems)


def test_a_skill_may_add_its_own_sections_between_steps_and_quality_bar() -> None:
    assert "The loop" in headings(assets.skill("wm-apply"))
    assert layout_problems("wm-apply", assets.skill("wm-apply")) == []


def test_a_missing_shared_rules_line_is_reported() -> None:
    text = assets.skill("wm-pr").replace(SHARED_LINE, "- Something else")
    assert layout_problems("wm-pr", text) == [
        "wm-pr: the first rule should point at the shared rules"
    ]


def section(text: str, heading: str) -> str:
    """The text of one `##` section, up to the next `##` heading."""
    _, _, rest = text.partition(f"\n## {heading}\n")
    return rest.split("\n## ", 1)[0]


def test_scenario_path_chosen_by_the_planner() -> None:
    """Requirement "Propose picks the path": the planner chooses, and tiny work waits for a yes."""
    text = assets.skill("wm-propose")
    steps = section(text, "Steps")
    assert "Investigate and choose the path" in steps
    assert "Don't ask them which path to take" in steps
    for path in ("**tiny**", "**short**", "**full**"):
        assert path in steps
    tiny = section(text, "The tiny path")
    assert "Build nothing until the human says yes." in tiny
    assert "go back to step 2 on the short or full path" in tiny


def test_scenario_open_questions() -> None:
    """Requirement "Propose picks the path": open questions put the change on the full path."""
    steps = section(assets.skill("wm-propose"), "Steps")
    assert "A question that is still open puts the change on the full path" in steps
    assert "`## Open questions`" in steps
    assert "Choose short only when no question is left." in steps


def test_scenario_no_tiny_path_offer() -> None:
    """Requirement "Explore's closing offers": four offers, none naming wm-fix."""
    offers = section(assets.skill("wm-explore"), "Closing offers")
    new, resumed = offer_lists(offers)
    assert (len(new), len(resumed)) == (4, 4)
    assert "wm-fix" not in offers


def offer_lists(offers: str) -> tuple[list[str], list[str]]:
    """The numbered offers for a new idea and for a resumed exploration."""
    new_part, _, resumed_part = offers.partition("For a resumed exploration:")
    _, _, new_part = new_part.partition("For a new idea:")

    def numbered(text: str) -> list[str]:
        return [line for line in text.splitlines() if line[:1].isdigit()]

    return numbered(new_part), numbered(resumed_part)


def test_scenario_started_with_an_explorations_name() -> None:
    """Requirement "Resuming an exploration": a named exploration is read and continued."""
    first = section(assets.skill("wm-explore"), "Steps").split("\n2. ", 1)[0]
    assert "name of an active exploration" in first
    assert "`wm show <exploration>`" in first
    assert "changed since" in first
    assert "continue from its Questions and Approaches" in first


def test_scenario_offers_for_a_resumed_exploration() -> None:
    """Requirement "Explore's closing offers": the four offers for a resumed exploration."""
    offers = section(assets.skill("wm-explore"), "Closing offers")
    _, resumed = offer_lists(offers)
    assert [line.split("**")[1] for line in resumed] == [
        "Do nothing.",
        "Update it.",
        "Start a proposal.",
        "Start a milestone",
    ]
    assert "wm exploration drop" in resumed[1]
    assert "--from <exploration>" in resumed[2]
    assert "--from <exploration>" in resumed[3]
    assert "never edit it by hand" in offers
    assert "led-to [" not in assets.skill("wm-explore")


def test_scenario_proposal_from_an_exploration() -> None:
    """Requirement "Explore's closing offers": wm-propose names the exploration with --from."""
    steps = section(assets.skill("wm-propose"), "Steps")
    naming = next(line for line in steps.splitlines() if line.startswith("3. **Name.**"))
    assert "--from <exploration>" in naming


def test_skills_reopen_a_revised_item_after_acceptance_and_what_a_decision_rebuilds() -> None:
    """Item 2.1 of reopen-ticked-items: the skills send a revised or rebuilt item back to apply."""
    update = section(assets.skill("wm-update"), "Steps")
    assert "once the human has accepted again, reopen it with `wm reopen" in update
    assert "`wm reopen` needs an accepted change" in update
    apply = assets.skill("wm-apply")
    assert "`revised-ticked-item` warning" in apply
    assert (
        'reopen each one after it with `wm reopen <name> <item> --reason "<the decision>"`' in apply
    )

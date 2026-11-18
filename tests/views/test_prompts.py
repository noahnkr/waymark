"""The prompts: key names in, an outcome and lines out, with no terminal."""

from collections.abc import Iterable
from typing import Any

import pytest

from waymark.services.setup import atlas_name_problem
from waymark.views.prompts import (
    Checklist,
    Choice,
    Confirm,
    Outcome,
    Prompt,
    Select,
    TextInput,
)
from waymark.views.style import Style

PLAIN = Style()
GLYPHS = Style(unicode=True)
KINDS = (Choice("A project", "project"), Choice("An atlas", "atlas", "several repos"))
TOOLS = (Choice("Claude Code", "claude-code", "found"), Choice("Other", "other"))


def answer(prompt: Prompt) -> Any:
    return prompt.value


def why(prompt: Prompt) -> str | None:
    return prompt.reason


def feed(prompt: Prompt, keys: Iterable[str]) -> Outcome:
    outcome = prompt.outcome
    for key in keys:
        outcome = prompt.handle(key)
    return outcome


def test_select_moves_with_the_arrows_and_picks_with_enter() -> None:
    select = Select("What is this repository?", KINDS)
    assert answer(select) == "project"
    assert feed(select, ["down"]) is Outcome.OPEN
    assert answer(select) == "atlas"
    assert feed(select, ["down"]) is Outcome.OPEN
    assert answer(select) == "project"
    assert feed(select, ["up", "enter"]) is Outcome.DONE
    assert answer(select) == "atlas"


def test_select_takes_a_number() -> None:
    select = Select("What is this repository?", KINDS)
    assert feed(select, ["2", "enter"]) is Outcome.DONE
    assert answer(select) == "atlas"


def test_select_draws_its_options_with_the_focus() -> None:
    select = Select("What is this repository?", KINDS)
    assert select.render(PLAIN) == [
        "What is this repository?",
        "  -> A project",
        "     An atlas  several repos",
    ]
    assert select.render(GLYPHS)[1] == "  → A project"


def test_checklist_toggles_with_space() -> None:
    checklist = Checklist("Which agent tools?", TOOLS, selected=["claude-code"])
    assert answer(checklist) == ("claude-code",)
    assert feed(checklist, ["down", "space"]) is Outcome.OPEN
    assert answer(checklist) == ("claude-code", "other")
    assert feed(checklist, ["up", "space", "enter"]) is Outcome.DONE
    assert answer(checklist) == ("other",)


def test_checklist_draws_marks_and_notes() -> None:
    checklist = Checklist("Which agent tools?", TOOLS, selected=["claude-code"])
    assert checklist.render(GLYPHS)[1:] == [
        "  → ✓ Claude Code  found",
        "    ○ Other",
    ]


def test_scenario_nothing_selected() -> None:
    """Requirement "Agent tools to choose from": Enter with nothing selected is refused."""
    checklist = Checklist("Which agent tools?", TOOLS, selected=["claude-code"])
    assert feed(checklist, ["space", "enter"]) is Outcome.OPEN
    assert "at least one" in (why(checklist) or "")
    assert "at least one" in checklist.render(PLAIN)[-1]
    assert feed(checklist, ["space"]) is Outcome.OPEN
    assert why(checklist) is None
    assert feed(checklist, ["enter"]) is Outcome.DONE


def test_confirm_takes_y_n_the_arrows_or_the_default() -> None:
    assert feed(Confirm("Add the CI workflow?"), ["enter"]) is Outcome.DONE
    yes = Confirm("Add the CI workflow?")
    feed(yes, ["enter"])
    assert answer(yes) is True
    no = Confirm("Add the CI workflow?", default=True)
    assert feed(no, ["n"]) is Outcome.DONE
    assert answer(no) is False
    switched = Confirm("Add the CI workflow?", default=False)
    feed(switched, ["right", "enter"])
    assert answer(switched) is True
    assert Confirm("Add the CI workflow?").render(PLAIN)[1] == "  -> Yes      No"


def test_text_input_types_and_erases() -> None:
    text = TextInput("Atlas name?")
    feed(text, ["s", "h", "o", "p", "x", "backspace"])
    assert answer(text) == "shop"
    assert text.render(PLAIN)[1] == "  -> shop"
    assert feed(text, ["enter"]) is Outcome.DONE


def test_scenario_invalid_atlas_name() -> None:
    """Requirement "Interactive init": the question stays open with the reason."""
    text = TextInput("Atlas name?", validate=atlas_name_problem)
    feed(text, [*"shop", "space", *"platform"])
    assert answer(text) == "shop platform"
    assert feed(text, ["enter"]) is Outcome.OPEN
    assert why(text) == atlas_name_problem("shop platform")
    assert why(text) is not None
    assert "can't be an atlas name" in text.render(PLAIN)[-1]
    feed(text, ["backspace"] * len(" platform"))
    feed(text, [*"-platform"])
    assert feed(text, ["enter"]) is Outcome.DONE
    assert answer(text) == "shop-platform"


@pytest.mark.parametrize(
    "prompt",
    [
        Select("What is this repository?", KINDS),
        Checklist("Which agent tools?", TOOLS, selected=["claude-code"]),
        Confirm("Add the CI workflow?"),
        TextInput("Atlas name?"),
    ],
)
def test_escape_cancels_any_prompt(prompt: Prompt) -> None:
    assert feed(prompt, ["down", "escape"]) is Outcome.CANCELED
    assert feed(prompt, ["enter"]) is Outcome.CANCELED


def test_a_question_needs_choices() -> None:
    with pytest.raises(ValueError, match="at least one choice"):
        Select("Nothing?", ())

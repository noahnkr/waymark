"""The questions an interactive ``wm init`` asks, under a step indicator.

``ask_answers`` asks whether the repository is a project or an atlas (and the
atlas's name), which agent tools to set up, and whether to add the CI workflow.
It asks through an ``Asker``: ``RawAsker`` draws each question in place in raw
mode, ``LineAsker`` asks it as numbered choices at a line. Nothing is written
here; the caller runs ``init_project`` with the answers once every question is
answered.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from waymark.views.prompts import Checklist, Choice, Confirm, Outcome, Prompt, Select, TextInput
from waymark.views.style import ACCENT, MUTED, OK, Style
from waymark.views.terminal import RawTerminal, ask, ask_by_line, read_line

STEPS = ("Repository", "Tools", "CI", "Done")


@dataclass(frozen=True)
class Tool:
    """An agent tool to offer: its adapter's name and title, and whether it was found here."""

    name: str
    title: str
    found: bool


@dataclass(frozen=True)
class Answers:
    """What the human chose: an atlas name or None for a project, the tools, and CI."""

    atlas: str | None
    tools: tuple[str, ...]
    ci: bool


def step_line(style: Style, current: int) -> str:
    """The step indicator: done steps filled, the current one marked, the rest open."""
    marks = []
    for index in range(len(STEPS)):
        if index < current:
            marks.append(style.paint(style.symbol("milestone_done"), OK))
        elif index == current:
            marks.append(style.paint(style.symbol("current"), ACCENT))
        else:
            marks.append(style.paint(style.symbol("todo"), MUTED))
    joint = f" {style.paint(style.symbol('rule') * 3, MUTED)} "
    names = style.paint(" · " if style.unicode else " - ", MUTED).join(
        style.paint(name, ACCENT) if index == current else name for index, name in enumerate(STEPS)
    )
    return f"{joint.join(marks)}  {names}"


class Asker(Protocol):
    """Asks one question at a step, and says how it ended."""

    def ask(self, prompt: Prompt, step: int) -> Outcome: ...


class RawAsker:
    """Asks in raw mode, redrawing the step indicator and the question in place."""

    def __init__(self, terminal: RawTerminal, style: Style) -> None:
        self.terminal = terminal
        self.style = style

    def ask(self, prompt: Prompt, step: int) -> Outcome:
        self.terminal.draw([step_line(self.style, step), ""])
        self.terminal.finish()
        return ask(prompt, self.terminal, self.style)


class LineAsker:
    """Asks at a line, as numbered choices, when raw mode isn't there."""

    def __init__(
        self,
        style: Style,
        read: Callable[[str], str] = read_line,
        write: Callable[[str], None] = print,
    ) -> None:
        self.style = style
        self.read = read
        self.write = write

    def ask(self, prompt: Prompt, step: int) -> Outcome:
        self.write("")
        self.write(step_line(self.style, step))
        return ask_by_line(prompt, self.style, self.read, self.write)


def tool_question(tools: Sequence[Tool]) -> Checklist:
    """Every tool, with the found ones selected and marked; all selected when none is found."""
    choices = [Choice(tool.title, tool.name, "found" if tool.found else "") for tool in tools]
    found = [tool.name for tool in tools if tool.found]
    selected = found or [tool.name for tool in tools]
    return Checklist("Which agent tools should wm set up?", choices, selected=selected)


def ask_answers(
    asker: Asker, tools: Sequence[Tool], validate_atlas: Callable[[str], str | None]
) -> Answers | None:
    """Ask the three questions; None when one of them is canceled."""
    kind = Select(
        "What is this repository?",
        [
            Choice("A project", "project", "one repository, its own record"),
            Choice("An atlas", "atlas", "a record that several code repos share"),
        ],
    )
    if asker.ask(kind, 0) is not Outcome.DONE:
        return None
    atlas = None
    if kind.value == "atlas":
        name = TextInput("What is the atlas's name?", validate=validate_atlas)
        if asker.ask(name, 0) is not Outcome.DONE:
            return None
        atlas = name.value
    chosen = tool_question(tools)
    if asker.ask(chosen, 1) is not Outcome.DONE:
        return None
    ci = Confirm('Add the CI workflow, which runs "wm check" in GitHub Actions?', default=True)
    if asker.ask(ci, 2) is not Outcome.DONE:
        return None
    return Answers(atlas, chosen.value, ci.value)

"""Questions as small state machines: they take key names and draw lines, with no terminal.

A prompt is fed one key at a time with ``handle``, which says whether the question
is still open, answered or canceled, and drawn with ``render`` in a ``Style``.
Keys are names: ``up``, ``down``, ``left``, ``right``, ``space``, ``enter``,
``escape``, ``backspace``, or a single typed character. Reading keys from a real
terminal, and drawing the lines there, is the job of ``views/terminal.py``.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from waymark.views.style import ACCENT, ATTENTION, MUTED, OK, STRONG, Style


class Outcome(StrEnum):
    """Where a question stands."""

    OPEN = "open"
    DONE = "done"
    CANCELED = "canceled"


@dataclass(frozen=True)
class Choice:
    """One option of a question: what it shows, what it stands for, and a note beside it."""

    label: str
    value: Any
    note: str = ""


class Prompt(ABC):
    """A question: keys go in, an outcome and lines come out."""

    def __init__(self, question: str) -> None:
        self.question = question
        self.outcome = Outcome.OPEN
        self.reason: str | None = None
        """Why the last Enter was refused, shown under the question until the next key."""

    def handle(self, key: str) -> Outcome:
        """Take one key, and say whether the question is still open."""
        if self.outcome is not Outcome.OPEN:
            return self.outcome
        if key == "escape":
            self.outcome = Outcome.CANCELED
            return self.outcome
        self.reason = None
        self._key(key)
        return self.outcome

    @abstractmethod
    def _key(self, key: str) -> None:
        """Act on a key other than Escape while the question is open."""

    @property
    @abstractmethod
    def value(self) -> Any:
        """The answer as it stands."""

    def render(self, style: Style) -> list[str]:
        """The question, its body, and the reason Enter was refused, if it was."""
        lines = [style.paint(self.question, STRONG), *self._body(style)]
        if self.reason:
            lines.append(style.paint(f"  {style.symbol('warning')} {self.reason}", ATTENTION))
        return lines

    @abstractmethod
    def _body(self, style: Style) -> list[str]:
        """The lines under the question."""


def _cursor(style: Style, here: bool) -> str:
    """The pointer before the focused option, or as many spaces."""
    arrow = style.symbol("arrow")
    return style.paint(arrow, ACCENT) if here else " " * len(arrow)


def _note(style: Style, note: str) -> str:
    return f"  {style.paint(note, MUTED)}" if note else ""


class _Options(Prompt):
    """A question over a list of choices, with a focused one moved by the arrows."""

    def __init__(self, question: str, choices: Sequence[Choice], focus: int = 0) -> None:
        super().__init__(question)
        if not choices:
            raise ValueError("A question needs at least one choice.")
        self.choices = tuple(choices)
        self.focus = focus

    def _move(self, key: str) -> bool:
        """Move the focus for an arrow key, wrapping around; say whether the key was one."""
        step = {"up": -1, "down": 1}.get(key)
        if step is None:
            return False
        self.focus = (self.focus + step) % len(self.choices)
        return True


class Select(_Options):
    """One of several: the arrows move, Enter picks the focused one."""

    def _key(self, key: str) -> None:
        if self._move(key):
            return
        if key.isdigit() and 1 <= int(key) <= len(self.choices):
            self.focus = int(key) - 1
        elif key == "enter":
            self.outcome = Outcome.DONE

    @property
    def value(self) -> Any:
        return self.choices[self.focus].value

    def _body(self, style: Style) -> list[str]:
        lines = []
        for index, choice in enumerate(self.choices):
            here = index == self.focus
            label = style.paint(choice.label, ACCENT) if here else choice.label
            lines.append(f"  {_cursor(style, here)} {label}{_note(style, choice.note)}")
        return lines


class Checklist(_Options):
    """Any of several, at least one: the arrows move, Space toggles, Enter confirms."""

    def __init__(
        self,
        question: str,
        choices: Sequence[Choice],
        selected: Sequence[Any] = (),
        focus: int = 0,
    ) -> None:
        super().__init__(question, choices, focus)
        self.selected = {index for index, c in enumerate(self.choices) if c.value in selected}

    def _key(self, key: str) -> None:
        if self._move(key):
            return
        if key == "space":
            self.selected ^= {self.focus}
        elif key == "enter":
            if self.selected:
                self.outcome = Outcome.DONE
            else:
                self.reason = "Select at least one: press Space to select."

    @property
    def value(self) -> tuple[Any, ...]:
        return tuple(c.value for index, c in enumerate(self.choices) if index in self.selected)

    def _body(self, style: Style) -> list[str]:
        lines = []
        for index, choice in enumerate(self.choices):
            on = index in self.selected
            mark = style.paint(style.symbol("done"), OK) if on else style.symbol("todo")
            here = index == self.focus
            label = style.paint(choice.label, ACCENT) if here else choice.label
            lines.append(f"  {_cursor(style, here)} {mark} {label}{_note(style, choice.note)}")
        return lines


class Confirm(Prompt):
    """Yes or no, with a default: y or n answers, the arrows switch, Enter takes it."""

    def __init__(self, question: str, default: bool = True) -> None:
        super().__init__(question)
        self.answer = default

    def _key(self, key: str) -> None:
        if key in ("left", "right", "up", "down"):
            self.answer = not self.answer
        elif key.lower() in ("y", "n"):
            self.answer = key.lower() == "y"
            self.outcome = Outcome.DONE
        elif key == "enter":
            self.outcome = Outcome.DONE

    @property
    def value(self) -> bool:
        return self.answer

    def _body(self, style: Style) -> list[str]:
        yes = style.paint("Yes", ACCENT, STRONG) if self.answer else style.paint("Yes", MUTED)
        no = style.paint("No", ACCENT, STRONG) if not self.answer else style.paint("No", MUTED)
        mark = style.symbol("arrow")
        return [
            f"  {mark if self.answer else ' ' * len(mark)} {yes}   "
            f"{mark if not self.answer else ' ' * len(mark)} {no}"
        ]


class TextInput(Prompt):
    """A line of text, checked by a validator that gives a reason or None when it is fine."""

    def __init__(
        self,
        question: str,
        validate: Callable[[str], str | None] = lambda _: None,
        text: str = "",
    ) -> None:
        super().__init__(question)
        self.validate = validate
        self.text = text

    def _key(self, key: str) -> None:
        if key == "backspace":
            self.text = self.text[:-1]
        elif key == "space":
            self.text += " "
        elif key == "enter":
            self.reason = self.validate(self.text)
            if self.reason is None:
                self.outcome = Outcome.DONE
        elif len(key) == 1 and key.isprintable():
            self.text += key

    @property
    def value(self) -> str:
        return self.text

    def _body(self, style: Style) -> list[str]:
        return [f"  {style.paint(style.symbol('arrow'), ACCENT)} {self.text}"]

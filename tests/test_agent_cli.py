"""The agent interface through the command line."""

import datetime
import json

import pytest

from tests.support import Workspace
from tests.views.validator import errors
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main
from waymark.services import lifecycle
from waymark.views.schemas import SCHEMAS

NAME = "add-limit"
DAY = datetime.date(2026, 1, 15)


class Terminal:
    """Runs wm inside a temporary project and captures what it prints."""

    def __init__(
        self,
        project: Workspace,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self.project = project
        self.capsys = capsys
        monkeypatch.chdir(project.root)

    def run(self, *arguments: str, expect: int = EXIT_OK) -> str:
        code = main(list(arguments))
        captured = self.capsys.readouterr()
        assert code == expect, captured.out + captured.err
        return captured.out + captured.err

    def json(self, *arguments: str) -> dict[str, object]:
        payload: dict[str, object] = json.loads(self.run(*arguments, "--json"))
        assert errors(payload, SCHEMAS[str(payload["schema"]).removeprefix("wm.")]) == []
        return payload


@pytest.fixture
def terminal(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Terminal:
    project.change()
    return Terminal(project, monkeypatch, capsys)


def test_instructions_default_to_the_only_change_and_its_next_step(terminal: Terminal) -> None:
    payload = terminal.json("instructions")
    assert (payload["change"], payload["step"]) == (NAME, "accept")
    text = terminal.run("instructions")
    assert "Step: accept for add-limit" in text
    assert "wm accept add-limit" in text
    assert "\x1b[" not in text


def test_instructions_for_a_named_step_carry_its_template(terminal: Terminal) -> None:
    payload = terminal.json("instructions", "tasks", "--change", NAME)
    assert payload["step"] == "tasks"
    text = terminal.run("instructions", "tasks", "--change", NAME)
    assert "Write: waymark/changes/add-limit/tasks.md  (exists; revise it)" in text
    assert "  | - [ ] 1.1 <What to build>" in text


def test_instructions_for_an_unknown_step_are_a_usage_error(terminal: Terminal) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["instructions", "deploy"])
    assert exit_info.value.code == EXIT_USAGE


def test_context_pack_is_printed_as_markdown_or_json(terminal: Terminal) -> None:
    lifecycle.accept(terminal.project.root, NAME, DAY)
    text = terminal.run("context", NAME, "1.1", "--for", "implement")
    assert text.startswith("# Context pack: implement add-limit 1.1\n")
    assert "RESULT: done | partial | spec-gap | blocked" in text
    payload = terminal.json("context", NAME, "1.1", "--for", "implement")
    assert payload["schema"] == "wm.context.implement"
    assert terminal.json("context", "--for", "explore")["schema"] == "wm.context.explore"


def test_context_pack_that_fails_the_delegation_gate_exits_1(terminal: Terminal) -> None:
    refusal = terminal.run("context", NAME, "1.1", "--for", "implement", expect=EXIT_REFUSED)
    assert refusal.startswith("wm: No implement context pack for add-limit 1.1:")
    assert "is not accepted" in refusal
    refusal = terminal.run("context", NAME, "--for", "review", expect=EXIT_REFUSED)
    assert "exactly one change and one item" in refusal


def test_context_needs_to_know_what_it_is_for(terminal: Terminal) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["context", NAME, "1.1"])
    assert exit_info.value.code == EXIT_USAGE

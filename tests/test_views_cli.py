"""The read commands through the command line: text, ``--json`` and exit codes."""

import json
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import Workspace, delta, requirement, spec
from tests.views.validator import errors
from waymark import __version__
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main
from waymark.views.schemas import SCHEMAS


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

    def json(self, *arguments: str, expect: int = EXIT_OK) -> dict[str, object]:
        payload: dict[str, object] = json.loads(self.run(*arguments, "--json", expect=expect))
        name = str(payload["schema"]).removeprefix("wm.")
        assert errors(payload, SCHEMAS[name]) == []
        return payload


@pytest.fixture
def terminal(
    project: Workspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Terminal:
    project.write("specs/search.md", spec())
    project.change("add-order", deltas={"search": delta(added=(requirement("Result order"),))})
    return Terminal(project, monkeypatch, capsys)


def test_every_read_command_has_a_json_form_that_matches_its_schema(terminal: Terminal) -> None:
    seen = {
        str(terminal.json(*arguments)["schema"])
        for arguments in (
            ["status"],
            ["inbox"],
            ["check"],
            ["ls", "changes"],
            ["ls", "specs"],
            ["ls", "milestones"],
            ["ls", "explorations"],
            ["show", "add-order"],
            ["show", "search"],
        )
    }
    assert seen == {"wm.status", "wm.inbox", "wm.check", "wm.ls", "wm.show.change", "wm.show.spec"}


def test_views_print_plain_text_when_piped(terminal: Terminal) -> None:
    for arguments in (["status"], ["inbox"], ["ls", "changes"], ["show", "add-order"]):
        text = terminal.run(*arguments)
        assert "\x1b[" not in text
        assert "add-order" in text


def test_status_runs_from_a_folder_inside_the_project(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = terminal.project.root / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert "add-order" in terminal.run("status")


def test_reads_work_when_the_pinned_version_differs(terminal: Terminal) -> None:
    terminal.project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    status = terminal.json("status")
    assert status["writable"] is False
    assert "pinned to 9.9.9" in terminal.run("status")
    assert terminal.json("check")["warnings"] == 1
    assert "pinned to wm 9.9.9" in terminal.run("accept", "add-order", expect=EXIT_REFUSED)


def test_check_exit_code_follows_its_errors_in_both_forms(terminal: Terminal) -> None:
    assert terminal.json("check")["errors"] == 0
    terminal.project.write("specs/Search_Two.md", spec())
    assert terminal.json("check", expect=EXIT_REFUSED)["errors"] == 1
    assert "1 error(s), 0 warning(s)." in terminal.run("check", expect=EXIT_REFUSED)


def test_show_refuses_an_unknown_name_with_exit_1(terminal: Terminal) -> None:
    refusal = terminal.run("show", "no-such-thing", expect=EXIT_REFUSED)
    assert refusal.startswith("wm: There is no change, spec, milestone or exploration named")


def test_show_takes_a_kind_when_a_name_is_shared(terminal: Terminal) -> None:
    terminal.project.write(
        "explorations/search.md",
        "# S\n\n## Context\n\n## Questions\n\n## Approaches\n\n## Conclusion\n\n## Related\n",
    )
    assert "--kind spec" in terminal.run("show", "search", expect=EXIT_REFUSED)
    assert terminal.json("show", "search", "--kind", "exploration")["schema"] == (
        "wm.show.exploration"
    )


def test_ls_can_include_the_archive(terminal: Terminal) -> None:
    terminal.project.write("changes/archive/2026-01-20-add-index/proposal.md", "# Old\n")
    assert "add-index" not in terminal.run("ls", "changes")
    assert "add-index" in terminal.run("ls", "changes", "--archived")


def test_ls_of_an_unknown_kind_is_a_usage_error(terminal: Terminal) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["ls", "things"])
    assert exit_info.value.code == EXIT_USAGE


def test_views_outside_a_project_say_how_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == EXIT_REFUSED
    assert "initialize" in capsys.readouterr().err


def test_close_runs_from_the_command_line(terminal: Terminal) -> None:
    terminal.run("new", "milestone", "tidy-docs")
    assert "Closed the milestone" in terminal.run("close", "tidy-docs")
    assert terminal.json("ls", "milestones")["entries"] == []
    assert "tidy-docs" in terminal.run("ls", "milestones", "--archived")

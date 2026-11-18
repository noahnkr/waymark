"""The read commands through the command line: text, ``--json`` and exit codes."""

import datetime
import io
import json
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import Workspace, delta, milestone, requirement, spec
from tests.views.validator import errors
from waymark import __version__
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main
from waymark.services import lifecycle
from waymark.views import payloads, render
from waymark.views.payloads import Payload
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style


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
    assert refusal.startswith(
        "wm: There is no change, spec, milestone, exploration or resource named"
    )


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


def resource_text(title: str, kind: str, serves: str, status: str) -> str:
    return (
        f"# {title}\n\n- Kind: {kind}\n- Serves: {serves}\n- Status: {status}\n"
        "- Verified: 2026-11-17\n\n## What it is\n\nIt.\n\n## Access\n\nNone.\n\n"
        "## Interface\n\nNone.\n\n## Data\n\nNone.\n\n## Configuration\n\n### prod\n\nLive.\n\n"
        "## Verification\n\nNone.\n"
    )


def test_scenario_listing(terminal: Terminal) -> None:
    """Requirement "Resource commands": wm ls resources gives kind, status and specs."""
    terminal.project.write("specs/billing.md", spec())
    terminal.project.write(
        "resources/stripe.md", resource_text("Stripe", "service", "billing", "active")
    )
    terminal.project.write(
        "resources/heroku.md", resource_text("Heroku", "platform", "none", "retired")
    )
    lines = terminal.run("ls", "resources").splitlines()
    assert [line.split() for line in lines] == [
        ["heroku", "retired", "platform,", "serves", "none"],
        ["stripe", "active", "service,", "serves", "billing"],
    ]
    payload = terminal.json("ls", "resources")
    assert payload["entries"] == [
        {"name": "heroku", "state": "retired", "detail": "platform, serves none"},
        {"name": "stripe", "state": "active", "detail": "service, serves billing"},
    ]


def test_show_a_resource_in_full(terminal: Terminal) -> None:
    terminal.project.write("specs/billing.md", spec())
    terminal.project.write(
        "resources/stripe.md", resource_text("Stripe", "service", "billing", "active")
    )
    payload = terminal.json("show", "stripe", "--kind", "resource")
    assert payload["schema"] == "wm.show.resource"
    assert (payload["kind"], payload["serves"], payload["status"], payload["verified"]) == (
        "service",
        ["billing"],
        "active",
        "2026-11-17",
    )
    sections = payload["sections"]
    assert isinstance(sections, dict)
    assert sections["Configuration"] == "### prod\n\nLive."
    text = terminal.run("show", "stripe", "--kind", "resource")
    assert "Kind: service" in text
    assert "Serves: billing" in text
    assert "Live." in text


def test_scenario_piped_output(terminal: Terminal, monkeypatch: pytest.MonkeyPatch) -> None:
    """Requirement "Color on a terminal": through the command line."""
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert "\x1b[" not in terminal.run("status")


def test_scenario_forced_color(terminal: Terminal, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert "\x1b[" in terminal.run("status")
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\x1b[" not in terminal.run("status")


def test_scenario_json(terminal: Terminal, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert "\x1b[" not in terminal.run("status", "--json")


class LegacyConsole(io.StringIO):
    """Output whose encoding is cp437, as on a legacy Windows console."""

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return "cp437"


STYLED = Style(color=True, unicode=True, width=80)
"""A terminal 80 columns wide that shows color and glyphs."""
NOW = datetime.datetime.now(datetime.UTC)


def test_status_colors_phases_bars_and_roadmaps(terminal: Terminal) -> None:
    """Item: status in the new style."""
    terminal.project.write(
        "milestones/faster-search/milestone.md",
        milestone("- add-order: results in order\n- add-cache: a cache\n"),
    )
    record = terminal.project.record()
    payload = payloads.status(record)
    phase = payload["changes"][0]["phase"]
    text = render.to_text(payload, STYLED)
    assert f"\x1b[2m{phase}" in text
    assert "\x1b[2m░░░░░░░░░░\x1b[0m" in text
    assert "faster-search" in text
    assert "\x1b[2m◇ ◇\x1b[0m" in text
    lifecycle.accept(terminal.project.root, "add-order", datetime.date(2026, 1, 15))
    accepted = render.to_text(payloads.status(terminal.project.record()), STYLED)
    assert "\x1b[36maccepted" in accepted


def test_check_groups_findings_by_file_and_colors_the_counts(terminal: Terminal) -> None:
    terminal.project.write("specs/Other.md", "# Search\n")
    text = render.to_text(payloads.check(terminal.project.record(), NOW), STYLED)
    assert "\x1b[1mspecs/Other.md\x1b[0m\n  \x1b[31merror\x1b[0m: invalid-name:" in text
    assert "\x1b[31m1 error(s)" in text
    plain = render.to_text(payloads.check(terminal.project.record(), NOW), Style())
    assert "specs/Other.md\n  error: invalid-name:" in plain


def test_inbox_wraps_its_summaries(terminal: Terminal) -> None:
    lifecycle.accept(terminal.project.root, "add-order", datetime.date(2026, 1, 15))
    reason = " ".join(["the wording waits on the product owner"] * 6)
    lifecycle.block(terminal.project.root, "add-order", "1.1", reason)
    payload = payloads.inbox(terminal.project.record())
    wrapped = render.to_text(payload, STYLED).split("\n")
    summary = [line for line in wrapped if "product owner" in line]
    assert len(summary) > 1
    assert all(len(line) <= 80 and line.startswith("      ") for line in summary)
    plain = render.to_text(payload, Style()).split("\n")
    assert len([line for line in plain if "product owner" in line]) == 1


WHY = " ".join(["Long result lists are slow to read and slower to load"] * 6)
"""One paragraph of about 300 characters."""


def long_why(terminal: Terminal) -> Payload:
    """The add-order change, with its Why one paragraph of about 300 characters."""
    folder = terminal.project.path("changes/add-order")
    text = (folder / "proposal.md").read_text(encoding="utf-8")
    text = text.replace("Long result lists are slow.", WHY)
    (folder / "proposal.md").write_text(text, encoding="utf-8")
    assert len(WHY) >= 300
    return payloads.show(terminal.project.record(), "add-order")


def test_scenario_legacy_console(terminal: Terminal) -> None:
    """Requirement "ASCII on consoles without the glyphs": a change with two items."""
    style = Style.detect(LegacyConsole(), {})
    assert not style.unicode
    payload = payloads.show(terminal.project.record(), "add-order")
    assert len(payload["items"]) == 2
    text = render.to_text(payload, style)
    text.encode("cp437")
    assert "  |- o 1.1" in text
    assert "  `- o 1.2" in text
    assert "  |   Criteria:" in text


def test_scenario_narrow_terminal(terminal: Terminal) -> None:
    """Requirement "Prose wrapped on a terminal": at 80 columns."""
    text = render.to_text(long_why(terminal), Style(unicode=True, width=80))
    lines = text.split("\n")
    start = lines.index("Why") + 1
    why = []
    for line in lines[start:]:
        if not line:
            break
        why.append(line)
    assert len(why) > 1
    assert all(len(line) <= 80 and line.startswith("  ") for line in why)
    assert " ".join(line.strip() for line in why) == WHY


def test_scenario_piped(terminal: Terminal) -> None:
    text = render.to_text(long_why(terminal), Style())
    assert f"\n  {WHY}\n" in text


def test_items_are_a_tree_with_records_on_the_stem(terminal: Terminal) -> None:
    lifecycle.accept(terminal.project.root, "add-order", datetime.date(2026, 1, 15))
    lifecycle.block(terminal.project.root, "add-order", "1.1", "waiting for the wording")
    payload = payloads.show(terminal.project.record(), "add-order")
    text = render.to_text(payload, Style(unicode=True, width=80))
    assert "  ├─ ○ 1.1" in text
    assert "  └─ ○ 1.2" in text
    assert "  │   (blocked)" in text
    colored = render.to_text(payload, STYLED)
    assert "\x1b[2m  │   (blocked)" in colored


def test_milestone_roadmap_marks(terminal: Terminal) -> None:
    terminal.project.write(
        "milestones/faster-search/milestone.md",
        milestone(
            "- [add-order](../../changes/add-order/proposal.md): order\n- add-cache: a cache\n"
        ),
    )
    payload = payloads.show(terminal.project.record(), "faster-search")
    text = render.to_text(payload, Style(unicode=True))
    assert "  ◇ add-order" in text
    assert "  ○ add-cache" in text
    ascii_text = render.to_text(payload, Style())
    assert "  o add-order" in ascii_text


LONG_CRITERIA = (
    "  - Criteria:\n"
    "    - " + " ".join(["the first criterion holds"] * 5) + "\n"
    "    - " + " ".join(["the second criterion holds"] * 5) + "\n"
    "  - Verify: a test\n"
)


def test_every_criterion_hangs_under_its_bullet(terminal: Terminal) -> None:
    """Item: the first bullet starts after its label and wraps like the rest."""
    folder = terminal.project.path("changes/add-order")
    tasks = (folder / "tasks.md").read_text(encoding="utf-8")
    head, rest = tasks.split("- [ ] 1.1", 1)
    title, after = rest.split("\n", 1)
    after = after[after.index("- [ ] 1.2") :]
    (folder / "tasks.md").write_text(
        f"{head}- [ ] 1.1{title}\n{LONG_CRITERIA}{after}", encoding="utf-8"
    )
    payload = payloads.show(terminal.project.record(), "add-order")
    lines = render.to_text(payload, Style(unicode=True, width=80)).split("\n")
    start = lines.index("  │   Criteria:")
    first, second = [i for i, line in enumerate(lines) if line.startswith("  │     - the ")]
    assert first == start + 1
    for index in (first, second):
        continuation = lines[index + 1]
        assert continuation.startswith("  │       ")
        assert continuation[len("  │       ")].isalpha()
        assert all(len(line) <= 80 for line in lines[index : index + 2])
    assert "  │   Verify: a test" in lines
    plain = render.to_text(payload, Style()).split("\n")
    assert "  │   Criteria:" not in plain
    assert "  |   Criteria:" in plain
    assert "  |   Verify: a test" in plain

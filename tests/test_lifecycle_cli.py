"""Full runs through the command line, each in a fresh temporary project."""

import datetime
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import DESIGN, delta, requirement
from waymark.cli import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, main
from waymark.record.project import find_project
from waymark.record.record import load_record
from waymark.record.state import StepKind, derive_state
from waymark.record.terms import Layout, Phase

TODAY = datetime.date.today().isoformat()
HEAD = "# Tasks\n\n## 1. Limit\n\n"


class Session:
    """A terminal in a temporary git repository."""

    def __init__(
        self, root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self.root = root
        self.capsys = capsys
        git_init(root)
        monkeypatch.chdir(root)

    def run(self, *arguments: str, expect: int = EXIT_OK) -> str:
        """Run wm; returns everything it printed."""
        code = main(list(arguments))
        captured = self.capsys.readouterr()
        assert code == expect, captured.out + captured.err
        if expect == EXIT_OK:
            assert captured.err == ""
        return captured.out + captured.err

    def write(self, relative: str, text: str) -> None:
        path = self.root / "waymark" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def read(self, relative: str) -> str:
        return (self.root / "waymark" / relative).read_bytes().decode("utf-8")

    def fill_proposal(self, name: str, impact: str = "Specs: search.") -> None:
        """Draft the proposal the way an agent would: by editing the skeleton."""
        text = self.read(f"changes/{name}/proposal.md")
        for hint, body in (
            ("<!-- The problem or opportunity, and why now. -->", "Long lists are slow."),
            ("<!-- What will be different once this change is archived. -->", "A capped list."),
            ("<!-- What this change deliberately does not do. -->", "Paging."),
        ):
            assert hint in text
            text = text.replace(hint, body)
        start = text.index("<!-- The specs this change touches")
        self.write(f"changes/{name}/proposal.md", text[:start] + impact + "\n")

    def step(self, name: str) -> tuple[Phase, StepKind, str | None]:
        state = derive_state(load_record(find_project(self.root))).changes[name]
        return state.phase, state.next_step.kind, state.next_step.item


@pytest.fixture
def session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Session:
    return Session(tmp_path / "project", monkeypatch, capsys)


def test_change_runs_from_init_to_archive_with_the_record_in_the_repo(session: Session) -> None:
    name = "add-limit"
    assert "kickoff" in session.run("init")
    assert "healthy" in session.run("check")

    session.run("new", "change", name)
    assert session.step(name) == (Phase.PROPOSED, StepKind.PROPOSE, None)
    session.fill_proposal(name)
    assert session.step(name) == (Phase.PROPOSED, StepKind.SPECS, None)

    session.write(
        f"changes/{name}/specs/search.md",
        delta(added=(requirement(),), purpose="How search behaves."),
    )
    assert session.step(name) == (Phase.SPECIFIED, StepKind.DESIGN, None)
    session.write(f"changes/{name}/design.md", DESIGN)
    assert session.step(name) == (Phase.DESIGNED, StepKind.TASKS, None)
    session.write(
        f"changes/{name}/tasks.md",
        HEAD
        + "- [ ] 1.1 Cap the results   `review: independent`\n  - Criteria: fifty at most\n"
        + "- [ ] 1.2 Explain the cap\n  - Criteria: the help text names the limit\n",
    )
    assert session.step(name) == (Phase.PLANNED, StepKind.ACCEPT, None)
    assert "healthy" in session.run("check")

    assert "is not accepted" in session.run("tick", name, "1.1", expect=EXIT_REFUSED)
    session.run("accept", name)
    assert session.step(name) == (Phase.ACCEPTED, StepKind.APPLY, "1.1")

    session.run("tick", name, "1.1")
    assert session.step(name) == (Phase.APPLYING, StepKind.REVIEW, "1.1")
    refusal = session.run("review", name, "1.1", "--self", "fine", expect=EXIT_REFUSED)
    assert "independent review" in refusal
    session.run("verdict", name, "1.1", "changes", "the bound is off by one")
    assert session.step(name) == (Phase.APPLYING, StepKind.APPLY, "1.1")
    session.run("reopen", name, "1.1")
    session.run("tick", name, "1.1")
    session.run("verdict", name, "1.1", "pass", "boundary covered")
    assert session.step(name) == (Phase.APPLYING, StepKind.APPLY, "1.2")

    session.run("block", name, "1.2", "waiting for the wording")
    assert session.step(name) == (Phase.APPLYING, StepKind.RESOLVE_ITEMS, "1.2")
    session.run("resolve", name, "1.2", "use the short wording")
    session.run("tick", name, "1.2")
    assert session.step(name) == (Phase.APPLYING, StepKind.REVIEW, "1.2")
    assert "missing the review record" in session.run(
        "archive", name, "--outcome", "Capped.", expect=EXIT_REFUSED
    )
    session.run("review", name, "1.2", "--self", "the help text names the limit")
    assert session.step(name) == (Phase.APPLIED, StepKind.ARCHIVE, None)
    assert "1 warning" in session.run("check")

    session.run("archive", name, "--outcome", "Results are capped at fifty.")
    record = load_record(find_project(session.root))
    assert record.problems == ()
    assert record.changes == {}
    assert [entry.path for entry in record.archived_changes] == [f"changes/archive/{TODAY}-{name}"]
    assert [item.name for item in record.specs["search"].requirements] == ["Result limit"]
    assert "healthy" in session.run("check")


def test_change_runs_from_init_to_archive_in_an_atlas_with_two_code_repos(
    session: Session,
) -> None:
    name = "add-limit"
    session.run("init", "--atlas", "suite")
    config = session.read("config.toml")
    session.write(
        "config.toml",
        config + '\n[atlas.repos.api]\npath = "../suite-api"\n\n[atlas.repos.web]\n',
    )
    for repo in ("suite-api", "suite-web"):
        git_init(session.root.parent / repo)
    record = load_record(find_project(session.root))
    assert record.layout is Layout.ATLAS
    assert record.problems == ()

    session.run("new", "change", name, "--owner", "Robin Roe")
    session.fill_proposal(name, "Specs: search. Repos: api, web.")
    session.write(
        f"changes/{name}/specs/search.md",
        delta(added=(requirement(),), purpose="How search behaves.", repos="api, web"),
    )
    session.write(f"changes/{name}/design.md", DESIGN)
    session.write(
        f"changes/{name}/tasks.md",
        HEAD + "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty at most\n"
        "- [ ] 1.2 Show the capped list\n  - Criteria: the page shows fifty rows\n  - Repo: web\n",
    )
    assert session.step(name) == (Phase.DESIGNED, StepKind.TASKS, None)
    assert "item-without-repo" in session.run("check", expect=EXIT_REFUSED)
    session.write(
        f"changes/{name}/tasks.md",
        HEAD + "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty at most\n  - Repo: api\n"
        "- [ ] 1.2 Show the capped list\n  - Criteria: the page shows fifty rows\n  - Repo: web\n",
    )
    session.run("accept", name)
    for number in ("1.1", "1.2"):
        session.run("tick", name, number)
        session.run("review", name, number, "--self", "matches the criteria")
    session.run("archive", name, "--outcome", "Capped in the API and shown in the web app.")

    record = load_record(find_project(session.root))
    assert record.problems == ()
    assert record.changes == {}
    assert record.specs["search"].repos == ("api", "web")
    assert not (session.root.parent / "suite-api" / "waymark").exists()
    assert not (session.root.parent / "suite-web" / "waymark").exists()


def test_small_change_takes_the_short_path_with_two_approvals(session: Session) -> None:
    name = "fix-typo"
    session.run("init")
    session.run("new", "change", name, "--short")
    session.fill_proposal(name, "No spec changes.")
    assert session.step(name) == (Phase.SPECIFIED, StepKind.TASKS, None)
    session.write(
        f"changes/{name}/tasks.md",
        HEAD + "- [ ] 1.1 Fix the word   `review: none`\n  - Criteria: the word is right\n",
    )
    session.run("accept", name)
    session.run("tick", name, "1.1")
    session.run("archive", name, "--outcome", "Typo fixed.")
    record = load_record(find_project(session.root))
    assert record.problems == ()
    assert record.changes == {}
    assert record.specs == {}


def test_override_archives_a_change_whose_review_is_missing(session: Session) -> None:
    name = "add-limit"
    session.run("init")
    session.run("new", "change", name, "--short")
    session.fill_proposal(name, "No spec changes.")
    session.write(
        f"changes/{name}/tasks.md", HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n"
    )
    session.run("accept", name)
    session.run("tick", name, "1.1")
    refusal = session.run("archive", name, "--outcome", "Done.", expect=EXIT_REFUSED)
    assert "--override" in refusal
    session.run("archive", name, "--outcome", "Done.", "--override", "checked by hand")
    text = session.read(f"changes/archive/{TODAY}-{name}/proposal.md")
    assert text.endswith("## Outcome\n\nDone.\n\nReview override: checked by hand\n")


def test_change_in_a_milestone_moves_its_roadmap_on(session: Session) -> None:
    name = "fix-typo"
    session.run("init")
    session.run("new", "milestone", "tidy-docs")
    session.run("new", "exploration", "wording")
    session.run("new", "change", name, "--short")
    session.fill_proposal(name, "No spec changes.")
    session.write(
        "milestones/tidy-docs/roadmap.md",
        f"# Tidy docs: roadmap\n\n- [ ] [Fix the typo](../../changes/{name}/proposal.md)\n",
    )
    session.write(f"changes/{name}/tasks.md", HEAD + "- [ ] 1.1 Fix the word   `review: none`\n")
    session.run("accept", name)
    session.run("tick", name, "1.1")
    session.run("sync", name, expect=EXIT_REFUSED)
    session.run("archive", name, "--outcome", "Fixed.")
    roadmap = session.read("milestones/tidy-docs/roadmap.md")
    assert f"- [x] [Fix the typo](../../changes/archive/{TODAY}-{name}/proposal.md)" in roadmap
    state = derive_state(load_record(find_project(session.root)))
    assert (state.milestones["tidy-docs"].archived, state.milestones["tidy-docs"].total) == (1, 1)


def test_refused_command_exits_1_and_says_what_to_do(session: Session) -> None:
    refusal = session.run("new", "change", "add-limit", expect=EXIT_REFUSED)
    assert refusal.startswith("wm: No Waymark project found")
    assert "initialize" in refusal
    session.run("init")
    assert "already has a record" in session.run("init", expect=EXIT_REFUSED)
    assert "There is no active change" in session.run("accept", "add-limit", expect=EXIT_REFUSED)


def test_check_exits_1_when_it_finds_errors(session: Session) -> None:
    session.run("init")
    session.write("specs/Search.md", "# Search\n")
    output = session.run("check", expect=EXIT_REFUSED)
    assert "error: specs/Search.md: invalid-name:" in output
    assert "1 error(s), 0 warning(s)." in output


def test_usage_errors_exit_2(session: Session) -> None:
    for arguments in (["new", "thing", "x"], ["verdict", "a", "1.1", "maybe", "r"], ["tick", "a"]):
        with pytest.raises(SystemExit) as exit_info:
            main(arguments)
        assert exit_info.value.code == EXIT_USAGE
        session.capsys.readouterr()


def test_options_for_a_change_are_refused_for_other_kinds(session: Session) -> None:
    session.run("init")
    assert "apply to a change only" in session.run(
        "new", "milestone", "tidy-docs", "--short", expect=EXIT_REFUSED
    )

"""The commands that write records: dated records under items and in the Log."""

import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from tests.support import TASKS, Workspace
from waymark.record import records
from waymark.record.atlas import Found, Location
from waymark.record.records import RecordKind
from waymark.record.state import AcceptanceState, StepKind
from waymark.record.terms import Verdict
from waymark.services import lifecycle
from waymark.services.common import Refusal
from waymark.services.pr import describe

NAME = "add-limit"
TASKS_FILE = f"changes/{NAME}/tasks.md"
PROPOSAL_FILE = f"changes/{NAME}/proposal.md"
DAY = datetime.date(2026, 11, 20)
NEXT = datetime.date(2026, 11, 21)


@pytest.fixture
def latest(project: Workspace) -> Workspace:
    """A project in a git repository, in the format this wm writes."""
    return project


def accepted(project: Workspace, tasks: str = TASKS) -> Workspace:
    project.change(tasks=tasks)
    lifecycle.accept(project.root, NAME, DAY)
    return project


def built(project: Workspace) -> Workspace:
    accepted(project)
    for number in ("1.1", "1.2"):
        lifecycle.tick(project.root, NAME, number)
    return project


def log(project: Workspace) -> str:
    text = project.read(TASKS_FILE)
    return text[text.index("## Log") :]


def test_scenario_acceptance_in_the_log(latest: Workspace) -> None:
    latest.change()
    before = latest.read(PROPOSAL_FILE)
    done = lifecycle.accept(latest.root, NAME, DAY)
    assert done.paths == (TASKS_FILE,)
    assert latest.read(PROPOSAL_FILE) == before
    lines = log(latest).splitlines()
    assert lines[0] == "## Log"
    assert lines[2].startswith("- (accepted) 2026-11-20 fingerprint ")
    assert lines[2].endswith(" items 1.1 1.2 by Sam Doe")
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_accepted_again(latest: Workspace) -> None:
    accepted(latest)
    latest.replace(
        TASKS_FILE,
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n",
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n"
        "- [ ] 1.3 Test it\n"
        "  - Criteria: done\n"
        "  - Verify: a test\n",
    )
    latest.replace(f"changes/{NAME}/design.md", "## Context", "## Context\n\nMore context.")
    assert latest.change_state().acceptance is AcceptanceState.WITHDRAWN
    lifecycle.accept(latest.root, NAME, NEXT)
    accepted_lines = [line for line in log(latest).splitlines() if "(accepted)" in line]
    assert len(accepted_lines) == 2
    assert accepted_lines[1].startswith("- (accepted) 2026-11-21 ")
    assert " items 1.1 1.2 1.3 by " in accepted_lines[1]
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_blocked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.2", "the API key is missing", DAY)
    assert "  - (blocked) 2026-11-20 by Sam Doe: the API key is missing\n" in latest.read(
        TASKS_FILE
    )


def test_scenario_record_added(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.2", "the key", DAY)
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_resolved_item_keeps_its_blocker(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1")
    lifecycle.block(latest.root, NAME, "1.2", "the API key is missing", DAY, by="Ada")
    lifecycle.resolve(latest.root, NAME, "1.2", "use the test key", NEXT)
    text = latest.read(TASKS_FILE)
    assert "  - (blocked) 2026-11-20 by Ada: the API key is missing\n" in text
    assert "  - (resolved) 2026-11-21 by Sam Doe: use the test key\n" in text
    step = latest.change_state().next_step
    assert (step.kind, step.item) == (StepKind.APPLY, "1.2")


def test_an_open_blocker_is_resolved_before_another(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.2", "the key", DAY)
    with pytest.raises(Refusal, match="open"):
        lifecycle.block(latest.root, NAME, "1.2", "the key again", DAY)


def test_a_gap_is_a_record_too(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.report_gap(latest.root, NAME, "1.2", "the maximum", DAY)
    assert "  - (gap) 2026-11-20 by Sam Doe: the maximum\n" in latest.read(TASKS_FILE)
    assert latest.record().changes[NAME].tasks.item("1.2").spec_gap == "the maximum"  # type: ignore[union-attr]


def test_scenario_note_on_an_unticked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.add_note(latest.root, NAME, "1.2", "the parser is done; the CLI flag is not", DAY)
    assert (
        "  - (note) 2026-11-20 by Sam Doe: the parser is done; the CLI flag is not\n"
        in latest.read(TASKS_FILE)
    )
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_note_on_a_ticked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1")
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match="already ticked"):
        lifecycle.add_note(latest.root, NAME, "1.1", "late", DAY)
    assert latest.read(TASKS_FILE) == before


def test_a_note_needs_an_accepted_change(latest: Workspace) -> None:
    latest.change()
    with pytest.raises(Refusal, match="not accepted"):
        lifecycle.add_note(latest.root, NAME, "1.1", "early", DAY)


def test_scenario_explicit_author(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(latest.root, NAME, "<summary>", DAY, by="Ada and Grace")
    assert "- (self-review) 2026-11-20 covers 1.1 1.2 by Ada and Grace: <summary>\n" in log(latest)


def test_a_name_with_a_colon_is_refused(latest: Workspace) -> None:
    built(latest)
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match='holds ": "'):
        lifecycle.self_review(latest.root, NAME, "fine", DAY, by="Ada: the planner")
    assert latest.read(TASKS_FILE) == before


def test_scenario_self_review_with_a_finding(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(
        latest.root, NAME, "<summary>", DAY, findings=["warning: src/a.py:12: <text>"]
    )
    text = latest.read(TASKS_FILE)
    assert text.endswith(
        "- (self-review) 2026-11-20 covers 1.1 1.2 by Sam Doe: <summary>\n"
        "  - warning `src/a.py:12`: <text>\n"
    )


def test_scenario_place_with_a_line_number(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(
        latest.root,
        NAME,
        "fine",
        DAY,
        findings=["warning: src/a.py:12: the limit is not checked"],
    )
    assert "  - warning `src/a.py:12`: the limit is not checked\n" in log(latest)


def test_a_place_holding_a_colon_and_space_goes_in_backticks(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(
        latest.root, NAME, "fine", DAY, findings=["suggestion: `docs: setup`: say it once"]
    )
    assert "  - suggestion `docs: setup`: say it once\n" in log(latest)
    [record] = latest.record().changes[NAME].tasks.review_records  # type: ignore[union-attr]
    assert record.findings[0].place == "docs: setup"


def test_a_changes_verdict_and_reopening_are_records(latest: Workspace) -> None:
    built(latest)
    lifecycle.verdict(
        latest.root,
        NAME,
        Verdict.CHANGES,
        "the cap is off by one",
        DAY,
        items=["1.1"],
        by="wm-reviewer",
    )
    assert (
        "- (review) 2026-11-20 changes 1.1 covers 1.1 1.2 by wm-reviewer: the cap is off by one\n"
        in log(latest)
    )
    lifecycle.reopen(latest.root, NAME, "1.1", NEXT)
    assert "  - (reopened) 2026-11-21 by Sam Doe\n" in latest.read(TASKS_FILE)
    assert not latest.record().changes[NAME].tasks.item("1.1").ticked  # type: ignore[union-attr]


def test_resolving_the_review_goes_in_the_log(latest: Workspace) -> None:
    built(latest)
    lifecycle.verdict(latest.root, NAME, Verdict.SPEC_GAP, "the maximum is unsaid", DAY)
    lifecycle.resolve(latest.root, NAME, "review", "fifty", NEXT)
    assert "- (resolved) 2026-11-21 by Sam Doe: fifty\n" in log(latest)


def test_sync_records_the_merge_and_keeps_the_acceptance(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(latest.root, NAME, "fine", DAY)
    before = latest.read(PROPOSAL_FILE)
    lifecycle.sync(latest.root, NAME, NEXT)
    assert latest.read(PROPOSAL_FILE) == before
    [synced] = [line for line in log(latest).splitlines() if "(synced)" in line]
    assert synced.startswith("- (synced) 2026-11-21 fingerprint ")
    assert synced.endswith(" by Sam Doe")
    change = latest.record().changes[NAME]
    assert change.synced == NEXT
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_not_reviewed(latest: Workspace) -> None:
    built(latest)
    with pytest.raises(Refusal, match="missing the self review"):
        lifecycle.archive(latest.root, NAME, DAY, built="Done.")


def test_scenario_overridden(latest: Workspace) -> None:
    built(latest)
    lifecycle.archive(latest.root, NAME, DAY, built="Done.", override="the reviewer is away")
    folder = f"changes/archive/{DAY.isoformat()}-{NAME}"
    tasks = latest.read(f"{folder}/tasks.md")
    assert "- (override) 2026-11-20 by Sam Doe: the reviewer is away\n" in tasks
    assert "override" not in latest.read(f"{folder}/proposal.md").casefold()
    body = describe(latest.record(), NAME)["body"]
    assert "Archived without its review by Sam Doe: the reviewer is away" in body
    assert body.count("the reviewer is away") == 1


def test_the_archived_change_reads_back_its_records(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(latest.root, NAME, "fine", DAY)
    lifecycle.archive(latest.root, NAME, DAY, built="Done.")
    from waymark.record.record import load_archived_change  # noqa: PLC0415

    record = latest.record()
    change = load_archived_change(record, record.archived_changes[0])
    assert change.problems == ()
    assert change.tasks is not None
    assert [r.kind for r in change.tasks.log] == [RecordKind.ACCEPTED, RecordKind.SELF_REVIEW]


SHOP = (("", PureWindowsPath("C:/work/shop")),)
ATLAS = (("", PurePosixPath("/work/atlas")), ("api", PurePosixPath("/home/sam/api")))


def self_review_with(latest: Workspace, finding: str) -> None:
    built(latest)
    lifecycle.self_review(latest.root, NAME, "fine", DAY, findings=[finding])


def test_scenario_absolute_path_inside_the_project(latest: Workspace) -> None:
    """Requirement "Finding places relative to the project"."""
    assert records.relative_place(r"C:\work\shop\src\limit.py:12", SHOP) == "src/limit.py:12"
    assert records.relative_place(r"c:\WORK\Shop\src\limit.py", SHOP) == "src/limit.py"
    place = f"{latest.root / 'src' / 'limit.py'}:12"
    self_review_with(latest, f"warning: {place}: the limit is not checked")
    assert "  - warning `src/limit.py:12`: the limit is not checked\n" in log(latest)


def test_an_absolute_place_keeps_what_follows_its_path(latest: Workspace) -> None:
    assert (
        records.relative_place(r"C:\work\shop\src\views\render.py: _spec_lines", SHOP)
        == "src/views/render.py: _spec_lines"
    )
    place = f"`{latest.root / 'src' / 'render.py'}: check`"
    self_review_with(latest, f"suggestion: {place}: group the findings")
    assert "  - suggestion `src/render.py: check`: group the findings\n" in log(latest)


def test_scenario_relative_path_with_backslashes(latest: Workspace) -> None:
    self_review_with(latest, r"suggestion: src\limit.py: name the constant")
    assert "  - suggestion `src/limit.py`: name the constant\n" in log(latest)


def test_a_place_that_isnt_a_path_is_kept(latest: Workspace) -> None:
    assert records.relative_place("the README's install section", SHOP) == (
        "the README's install section"
    )
    self_review_with(latest, "suggestion: docs: setup wording: say it once")
    assert "  - suggestion `docs`: setup wording: say it once\n" in log(latest)


def test_scenario_code_repo_of_an_atlas(
    latest: Workspace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert records.relative_place("/home/sam/api/src/limit.py:12", ATLAS) == "api/src/limit.py:12"
    api = tmp_path / "api"
    api.mkdir()
    here = Location("api", api, Found.REGISTRY)
    monkeypatch.setattr(lifecycle, "repo_locations", lambda _: {"api": here})
    built(latest)
    lifecycle.verdict(
        latest.root,
        NAME,
        Verdict.PASS,
        "fine",
        DAY,
        findings=[f"warning: {api / 'src' / 'limit.py'}:12: the limit is not checked"],
        by="wm-reviewer",
    )
    assert "  - warning `api/src/limit.py:12`: the limit is not checked\n" in log(latest)


def test_scenario_absolute_path_elsewhere(latest: Workspace, tmp_path: Path) -> None:
    assert records.relative_place("/home/sam/elsewhere/a.py", ATLAS) is None
    assert records.relative_place(r"D:\other\a.py", SHOP) is None
    built(latest)
    before = log(latest)
    elsewhere = tmp_path / "elsewhere" / "limit.py"
    with pytest.raises(Refusal, match="relative to the project"):
        lifecycle.self_review(
            latest.root,
            NAME,
            "fine",
            DAY,
            findings=[f"warning: {elsewhere}:12: the limit is not checked"],
        )
    assert log(latest) == before

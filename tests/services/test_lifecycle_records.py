"""The commands that write records: dated records in the Log, naming an item when about one."""

import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from tests.support import TASKS, Workspace, proposal
from waymark.record.evidence import records
from waymark.record.evidence.records import RecordKind
from waymark.record.machine.atlas import Found, Location
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
        lifecycle.tick(project.root, NAME, number, DAY)
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
    assert lines[2].startswith("- 2026-11-20 (accepted) fingerprint ")
    assert lines[2].endswith(" items 1.1, 1.2 by Sam Doe")
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_accepted_again(latest: Workspace) -> None:
    accepted(latest)
    latest.replace(
        TASKS_FILE,
        "- [ ] 1.2 Document the limit\n  - **Build:** planner\n"
        "  - **Criteria:** the help text names the limit\n"
        "  - **Verify:** read the help text\n",
        "- [ ] 1.2 Document the limit\n  - **Build:** planner\n"
        "  - **Criteria:** the help text names the limit\n"
        "  - **Verify:** read the help text\n"
        "- [ ] 1.3 Test it\n  - **Build:** planner\n"
        "  - **Criteria:** done\n"
        "  - **Verify:** a test\n",
    )
    latest.replace(f"changes/{NAME}/design.md", "## Context", "## Context\n\nMore context.")
    assert latest.change_state().acceptance is AcceptanceState.WITHDRAWN
    lifecycle.revise(latest.root, NAME, "more context", NEXT, parts=["design"])
    lifecycle.accept(latest.root, NAME, NEXT)
    accepted_lines = [line for line in log(latest).splitlines() if "(accepted)" in line]
    assert len(accepted_lines) == 2
    assert accepted_lines[1].startswith("- 2026-11-21 (accepted) ")
    assert " items 1.1, 1.2, 1.3 by " in accepted_lines[1]
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_blocked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.2", "the API key is missing", DAY)
    text = latest.read(TASKS_FILE)
    assert text.endswith(
        "\n- 2026-11-20 (blocked) 1.2 by planner for Sam Doe: the API key is missing\n"
    )
    assert "(blocked)" not in text.split("## Log")[0]


def test_scenario_revision_recorded(latest: Workspace) -> None:
    """Requirement "Revisions recorded": why an accepted change was edited, and what changed."""
    accepted(latest)
    latest.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(latest.root, NAME, "the count was 2, not 11", DAY, parts=["1.2"])
    assert latest.read(TASKS_FILE).endswith(
        "\n- 2026-11-20 (revised) 1.2 by planner for Sam Doe: the count was 2, not 11\n"
    )


def test_scenario_accepting_again_without_a_revision(latest: Workspace) -> None:
    """Requirement "Revisions recorded": accepting again needs a revision first."""
    accepted(latest)
    latest.replace(f"changes/{NAME}/design.md", "## Context", "## Context\n\nMore context.")
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match="wm revise"):
        lifecycle.accept(latest.root, NAME, NEXT)
    assert latest.read(TASKS_FILE) == before


def test_scenario_accepting_again_after_a_revision(latest: Workspace) -> None:
    """Requirement "Revisions recorded": once revised, the change can be accepted again."""
    accepted(latest)
    latest.replace(f"changes/{NAME}/design.md", "## Context", "## Context\n\nMore context.")
    lifecycle.revise(latest.root, NAME, "more context", NEXT, parts=["design"])
    lifecycle.accept(latest.root, NAME, NEXT)
    kinds = [line.split(" ", 3)[2] for line in log(latest).splitlines() if line.startswith("- ")]
    assert kinds[-2:] == ["(revised)", "(accepted)"]
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_unknown_part(latest: Workspace) -> None:
    """Requirement "Revisions recorded": a part the change doesn't have is refused."""
    accepted(latest)
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match=r"Item 3.1"):
        lifecycle.revise(latest.root, NAME, "<why>", DAY, parts=["3.1"])
    for part in ("specs/other", "tests"):
        with pytest.raises(Refusal, match=part):
            lifecycle.revise(latest.root, NAME, "<why>", DAY, parts=[part])
    assert latest.read(TASKS_FILE) == before


def test_a_change_never_accepted_is_not_revised(latest: Workspace) -> None:
    latest.change(tasks=TASKS)
    with pytest.raises(Refusal, match="never been accepted"):
        lifecycle.revise(latest.root, NAME, "<why>", DAY)


def test_scenario_planners_note(latest: Workspace) -> None:
    """Requirement "Who wrote a record": the planner's note names the planner and the human."""
    accepted(latest)
    lifecycle.add_note(latest.root, NAME, "1.2", "the parser is done", DAY)
    assert latest.read(TASKS_FILE).endswith(
        "\n- 2026-11-20 (note) 1.2 by planner for Sam Doe: the parser is done\n"
    )


def test_scenario_humans_acceptance(latest: Workspace) -> None:
    """Requirement "Who wrote a record": the human's acceptance names the git user alone."""
    accepted(latest)
    [line] = [line for line in latest.read(TASKS_FILE).splitlines() if "(accepted)" in line]
    assert line.endswith(" by Sam Doe")


def test_scenario_planners_item_ticked(latest: Workspace) -> None:
    """Requirement "Item records": a planner item's tick names the planner, and keeps acceptance."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    text = latest.read(TASKS_FILE)
    assert "- [x] 1.1" in text
    assert text.endswith("\n- 2026-11-20 (ticked) 1.1 by planner for Sam Doe\n")
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_humans_item_ticked(latest: Workspace) -> None:
    """Requirement "Item records": the tick of an item the human did names the human."""
    accepted(
        latest,
        TASKS.replace(
            "  - **Build:** planner\n  - **Criteria:** the help",
            "  - **Build:** human\n  - **Criteria:** the help",
        ),
    )
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    assert latest.read(TASKS_FILE).endswith("\n- 2026-11-20 (ticked) 1.2 by Sam Doe\n")


def test_scenario_implementers_item_ticked(latest: Workspace) -> None:
    """Requirement "Item records": an implementer's tick, recorded from its ending."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY, by="implementer")
    assert latest.read(TASKS_FILE).endswith("\n- 2026-11-20 (ticked) 1.1 by implementer\n")


def test_scenario_record_added(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.2", "the key", DAY)
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_resolved_item_keeps_its_blocker(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    lifecycle.block(latest.root, NAME, "1.2", "the API key is missing", DAY, by="Ada")
    lifecycle.resolve(latest.root, NAME, "1.2", "use the test key", NEXT)
    text = latest.read(TASKS_FILE)
    assert "- 2026-11-20 (blocked) 1.2 by Ada: the API key is missing\n" in text
    assert "- 2026-11-21 (resolved) 1.2 by Sam Doe: use the test key\n" in text
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
    assert "- 2026-11-20 (gap) 1.2 by planner for Sam Doe: the maximum\n" in latest.read(TASKS_FILE)
    assert latest.record().changes[NAME].tasks.item("1.2").spec_gap == "the maximum"  # type: ignore[union-attr]


def test_scenario_note_on_an_unticked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.add_note(latest.root, NAME, "1.2", "the parser is done; the CLI flag is not", DAY)
    assert (
        "- 2026-11-20 (note) 1.2 by planner for Sam Doe: the parser is done; the CLI flag is not\n"
        in latest.read(TASKS_FILE)
    )
    assert latest.change_state().acceptance is AcceptanceState.VALID


def test_scenario_note_on_a_ticked_item(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
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
    assert "- 2026-11-20 (self-review) covers 1.1, 1.2 by Ada and Grace: <summary>\n" in log(latest)


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
        "- 2026-11-20 (self-review) covers 1.1, 1.2 by planner for Sam Doe: <summary>\n"
        "  - [warning] `src/a.py:12`: <text>\n"
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
    assert "  - [warning] `src/a.py:12`: the limit is not checked\n" in log(latest)


def test_a_place_holding_a_colon_and_space_goes_in_backticks(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(
        latest.root, NAME, "fine", DAY, findings=["suggestion: `docs: setup`: say it once"]
    )
    assert "  - [suggestion] `docs: setup`: say it once\n" in log(latest)
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
        by="reviewer",
    )
    assert (
        "- 2026-11-20 (review) changes 1.1; covers 1.1, 1.2 by reviewer: the cap is off by one\n"
        in log(latest)
    )
    lifecycle.reopen(latest.root, NAME, "1.1", NEXT)
    assert "- 2026-11-21 (reopened) 1.1 by planner for Sam Doe\n" in latest.read(TASKS_FILE)
    assert not latest.record().changes[NAME].tasks.item("1.1").ticked  # type: ignore[union-attr]


def test_resolving_the_review_goes_in_the_log(latest: Workspace) -> None:
    built(latest)
    lifecycle.verdict(latest.root, NAME, Verdict.SPEC_GAP, "the maximum is unsaid", DAY)
    lifecycle.resolve(latest.root, NAME, "review", "fifty", NEXT)
    assert "- 2026-11-21 (resolved) by Sam Doe: fifty\n" in log(latest)


def test_sync_records_the_merge_and_keeps_the_acceptance(latest: Workspace) -> None:
    built(latest)
    lifecycle.self_review(latest.root, NAME, "fine", DAY)
    before = latest.read(PROPOSAL_FILE)
    lifecycle.sync(latest.root, NAME, NEXT)
    assert latest.read(PROPOSAL_FILE) == before
    [synced] = [line for line in log(latest).splitlines() if "(synced)" in line]
    assert synced.startswith("- 2026-11-21 (synced) fingerprint ")
    assert synced.endswith(" by planner for Sam Doe")
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
    assert "- 2026-11-20 (override) by Sam Doe: the reviewer is away\n" in tasks
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
    assert [r.kind for r in change.tasks.log] == [
        RecordKind.ACCEPTED,
        RecordKind.TICKED,
        RecordKind.TICKED,
        RecordKind.SELF_REVIEW,
        RecordKind.ARCHIVED,
    ]


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
    assert "  - [warning] `src/limit.py:12`: the limit is not checked\n" in log(latest)


def test_an_absolute_place_keeps_what_follows_its_path(latest: Workspace) -> None:
    assert (
        records.relative_place(r"C:\work\shop\src\views\render.py: _spec_lines", SHOP)
        == "src/views/render.py: _spec_lines"
    )
    place = f"`{latest.root / 'src' / 'render.py'}: check`"
    self_review_with(latest, f"suggestion: {place}: group the findings")
    assert "  - [suggestion] `src/render.py: check`: group the findings\n" in log(latest)


def test_scenario_relative_path_with_backslashes(latest: Workspace) -> None:
    self_review_with(latest, r"suggestion: src\limit.py: name the constant")
    assert "  - [suggestion] `src/limit.py`: name the constant\n" in log(latest)


def test_a_place_that_isnt_a_path_is_kept(latest: Workspace) -> None:
    assert records.relative_place("the README's install section", SHOP) == (
        "the README's install section"
    )
    self_review_with(latest, "suggestion: docs: setup wording: say it once")
    assert "  - [suggestion] `docs`: setup wording: say it once\n" in log(latest)


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
        by="reviewer",
    )
    assert "  - [warning] `api/src/limit.py:12`: the limit is not checked\n" in log(latest)


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


def test_a_place_with_a_backslash_in_prose_is_kept() -> None:
    """Requirement "Finding places relative to the project": a place that isn't a path."""
    assert records.relative_place(r"`re \d+` pattern", SHOP) == r"`re \d+` pattern"
    assert records.relative_place(r"src\limit.py:3", SHOP) == "src/limit.py:3"


def test_an_absolute_path_through_dot_dot_is_resolved() -> None:
    assert records.relative_place(r"C:\work\shop\..\shop\src\a.py", SHOP) == "src/a.py"
    assert records.relative_place(r"C:\work\shop\..\other\a.py", SHOP) is None
    assert records.relative_place("/home/sam/api/../api/b.py", ATLAS) == "api/b.py"


TWO = ("the parser is done", "the CLI flag is not")
UNDER = "  - the parser is done\n  - the CLI flag is not\n"


def test_scenario_note_with_details(latest: Workspace) -> None:
    """Requirement "Details under a record": each detail is a sub-bullet, in order."""
    accepted(latest)
    lifecycle.add_note(latest.root, NAME, "1.2", "partly built", DAY, details=TWO)
    assert latest.read(TASKS_FILE).endswith(
        "\n- 2026-11-20 (note) 1.2 by planner for Sam Doe: partly built\n" + UNDER
    )


def test_scenario_self_review_with_a_finding_and_details(latest: Workspace) -> None:
    """Requirement "Review recorded in the task list": findings come first, then details."""
    built(latest)
    lifecycle.self_review(
        latest.root,
        NAME,
        "every criterion holds",
        DAY,
        findings=["suggestion: src/a.py: name the constant"],
        details=["pytest passes", "wm check is healthy"],
    )
    assert latest.read(TASKS_FILE).endswith(
        ": every criterion holds\n"
        "  - [suggestion] `src/a.py`: name the constant\n"
        "  - pytest passes\n"
        "  - wm check is healthy\n"
    )


def test_scenario_detail_that_looks_like_a_finding(latest: Workspace) -> None:
    """Requirement "Details under a record": a detail with a bracketed severity is refused."""
    accepted(latest)
    before = latest.read(TASKS_FILE)
    for detail in ("[warning] not a finding", "", "two\nlines"):
        with pytest.raises(Refusal):
            lifecycle.add_note(latest.root, NAME, "1.2", "<text>", DAY, details=[detail])
    assert latest.read(TASKS_FILE) == before
    with pytest.raises(Refusal, match="severity in brackets"):
        lifecycle.add_note(latest.root, NAME, "1.2", "<text>", DAY, details=["[warning] x"])


def test_block_gap_resolve_verdict_and_revise_take_details(latest: Workspace) -> None:
    accepted(latest)
    lifecycle.block(latest.root, NAME, "1.1", "stuck", DAY, details=TWO)
    assert log(latest).endswith(": stuck\n" + UNDER)
    lifecycle.resolve(latest.root, NAME, "1.1", "go on", DAY, details=TWO)
    assert log(latest).endswith(": go on\n" + UNDER)
    lifecycle.report_gap(latest.root, NAME, "1.2", "unclear", DAY, details=TWO)
    assert log(latest).endswith(": unclear\n" + UNDER)
    latest.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(latest.root, NAME, "reworded", DAY, parts=["1.2"], details=TWO)
    assert log(latest).endswith(": reworded\n" + UNDER)


def test_verdict_takes_details(latest: Workspace) -> None:
    latest.change(tasks=TASKS, proposal_text=proposal(review="independent"))
    lifecycle.accept(latest.root, NAME, DAY)
    for number in ("1.1", "1.2"):
        lifecycle.tick(latest.root, NAME, number, DAY)
    lifecycle.verdict(latest.root, NAME, Verdict.PASS, "fine", DAY, by="reviewer", details=TWO)
    assert log(latest).endswith(" by reviewer: fine\n" + UNDER)


def test_scenario_details_in_the_views(latest: Workspace) -> None:
    """Requirement "Details under a record": wm show, both packs and wm pr show details."""
    from waymark.services.context import context_pack  # noqa: PLC0415
    from waymark.views import payloads, render  # noqa: PLC0415
    from waymark.views.style import Style  # noqa: PLC0415

    accepted(latest)
    lifecycle.add_note(latest.root, NAME, "1.2", "partly built", DAY, details=TWO)
    shown = payloads.show(latest.record(), NAME)
    [note] = next(item for item in shown["items"] if item["number"] == "1.2")["records"]
    assert note["details"] == list(TWO)
    assert "  - the CLI flag is not" in render.to_text(shown, Style(width=100))

    implement = context_pack(latest.record(), "implement", NAME, "1.2")
    assert implement["item"]["notes"] == [{"text": "partly built", "details": list(TWO)}]
    assert "  - the parser is done" in render.to_text(implement, Style())

    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    lifecycle.self_review(latest.root, NAME, "fine", DAY, details=["pytest passes"])
    assert "  - pytest passes" in describe(latest.record(), NAME)["body"]


def test_the_review_pack_shows_the_details_of_earlier_reviews(latest: Workspace) -> None:
    from waymark.services.context import context_pack  # noqa: PLC0415

    latest.change(tasks=TASKS, proposal_text=proposal(review="independent"))
    lifecycle.accept(latest.root, NAME, DAY)
    for number in ("1.1", "1.2"):
        lifecycle.tick(latest.root, NAME, number, DAY)
    lifecycle.verdict(
        latest.root,
        NAME,
        Verdict.CHANGES,
        "off by one",
        DAY,
        items=["1.1"],
        by="reviewer",
        details=["fifty-one come back"],
    )
    lifecycle.reopen(latest.root, NAME, "1.1", DAY)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    built = context_pack(latest.record(), "review", NAME, None)
    assert [review["details"] for review in built["reviews"]] == [["fifty-one come back"]]


def test_a_detail_starting_with_a_severity_word_reads_back_as_a_detail(latest: Workspace) -> None:
    """Item 2.3: only a line with a finding's shape is reported as a finding."""
    built(latest)
    lifecycle.self_review(
        latest.root, NAME, "fine", DAY, details=["warning signs remain", "critical path covered"]
    )
    change = latest.record().changes[NAME]
    assert change.problems == ()
    assert change.tasks is not None
    [review] = [r for r in change.tasks.log if r.kind is RecordKind.SELF_REVIEW]
    assert review.details == ("warning signs remain", "critical path covered")


def test_scenario_detail_with_a_findings_shape_but_no_brackets(latest: Workspace) -> None:
    """Requirement "Details under a record": a finding's shape is refused, bracketed or not."""
    built(latest)
    before = latest.read(TASKS_FILE)
    for detail in ("warning: the retry is slow", "critical `path` covered"):
        with pytest.raises(Refusal, match="finding's shape"):
            lifecycle.self_review(latest.root, NAME, "<summary>", DAY, details=[detail])
    assert latest.read(TASKS_FILE) == before


def test_scenario_detail_that_starts_with_a_severity_word(latest: Workspace) -> None:
    """Requirement "Details under a record": other text starting with a severity word is fine."""
    built(latest)
    lifecycle.self_review(latest.root, NAME, "<summary>", DAY, details=["warning signs remain"])
    assert latest.read(TASKS_FILE).endswith(": <summary>\n  - warning signs remain\n")
    assert latest.record().changes[NAME].problems == ()


def test_a_reviewers_detail_with_a_findings_shape_is_refused(latest: Workspace) -> None:
    from waymark.hooks.decide import decide  # noqa: PLC0415
    from waymark.hooks.events import Event, EventKind, Role  # noqa: PLC0415

    latest.change(tasks=TASKS, proposal_text=proposal(review="independent"))
    lifecycle.accept(latest.root, NAME, DAY)
    for number in ("1.1", "1.2"):
        lifecycle.tick(latest.root, NAME, number, DAY)
    before = latest.read(TASKS_FILE)
    message = "DETAIL: warning: the retry is slow\nCHANGE: add-limit\nVERDICT: pass: fine"
    event = Event(EventKind.AGENT_STOP, latest.root, role=Role.REVIEWER, message=message)
    decision = decide(event, DAY)
    assert not decision.allow
    assert "finding's shape" in decision.reason
    assert latest.read(TASKS_FILE) == before


def test_scenario_ticked_item_reopened_with_a_reason(latest: Workspace) -> None:
    """Requirement "Reopening a ticked item": the tick comes off, with the reason recorded."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    lifecycle.reopen(latest.root, NAME, "1.1", DAY, reason="its criteria changed")
    text = latest.read(TASKS_FILE)
    assert "- [ ] 1.1" in text
    assert text.endswith(
        "\n- 2026-11-20 (reopened) 1.1 by planner for Sam Doe: its criteria changed\n"
    )
    state = latest.change_state()
    assert state.acceptance is AcceptanceState.VALID
    assert (state.next_step.kind, state.next_step.item) == (StepKind.APPLY, "1.1")


def test_scenario_reopened_with_a_reason(latest: Workspace) -> None:
    """Requirement "Item records": a (reopened) record may carry a reason."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    lifecycle.reopen(latest.root, NAME, "1.2", DAY, reason="its criteria changed")
    assert log(latest).endswith("(reopened) 1.2 by planner for Sam Doe: its criteria changed\n")
    assert latest.record().changes[NAME].problems == ()


def test_scenario_no_reason_given(latest: Workspace) -> None:
    """Requirement "Reopening a ticked item": no review names it, so a reason is needed."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.1", DAY)
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match="--reason"):
        lifecycle.reopen(latest.root, NAME, "1.1", DAY)
    assert latest.read(TASKS_FILE) == before


def test_scenario_item_not_ticked(latest: Workspace) -> None:
    """Requirement "Reopening a ticked item": an item still to apply isn't reopened."""
    accepted(latest)
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match=r"isn't ticked"):
        lifecycle.reopen(latest.root, NAME, "1.1", DAY, reason="<why>")
    assert latest.read(TASKS_FILE) == before


def test_an_unaccepted_change_is_not_reopened(latest: Workspace) -> None:
    latest.change(tasks=TASKS)
    with pytest.raises(Refusal):
        lifecycle.reopen(latest.root, NAME, "1.1", DAY, reason="<why>")


def test_scenario_item_reopened_after_a_pass(latest: Workspace) -> None:
    """Requirement "Review of items added after a review": a reopened item is reviewed again."""
    built(latest)
    lifecycle.self_review(latest.root, NAME, "fine", DAY)
    assert latest.change_state().applied
    lifecycle.reopen(latest.root, NAME, "1.2", DAY, reason="its criteria changed")
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    state = latest.change_state()
    assert state.next_step.kind is StepKind.REVIEW
    assert state.review.uncovered == ("1.2",)
    with pytest.raises(Refusal, match=r"1\.2"):
        lifecycle.archive(latest.root, NAME, DAY, built="Done.")
    lifecycle.self_review(latest.root, NAME, "rebuilt", DAY)
    assert log(latest).endswith("(self-review) covers 1.2 by planner for Sam Doe: rebuilt\n")
    assert latest.change_state().applied


def revised_codes(project: Workspace) -> list[tuple[str, str]]:
    from waymark.services import check  # noqa: PLC0415

    found = check.check(project.root, datetime.datetime(2026, 11, 20, tzinfo=datetime.UTC))
    return [(f.code, f.message) for f in found if f.code == "revised-ticked-item"]


def test_scenario_revised_item_still_ticked(latest: Workspace) -> None:
    """Requirement "Revised item left ticked": a revision of a ticked item is reported."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    latest.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(latest.root, NAME, "reworded", DAY, parts=["1.2"])
    [(_, message)] = revised_codes(latest)
    assert "Item 1.2 was revised after it was ticked" in message
    assert "wm reopen add-limit 1.2" in message


def test_scenario_revised_item_reopened(latest: Workspace) -> None:
    """Requirement "Revised item left ticked": a reopen settles it."""
    accepted(latest)
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    latest.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(latest.root, NAME, "reworded", DAY, parts=["1.2"])
    lifecycle.accept(latest.root, NAME, DAY)
    lifecycle.reopen(latest.root, NAME, "1.2", DAY, reason="its criteria changed")
    assert revised_codes(latest) == []


def test_scenario_revised_item_not_yet_ticked(latest: Workspace) -> None:
    """Requirement "Revised item left ticked": an item still to apply isn't reported."""
    accepted(latest)
    latest.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(latest.root, NAME, "reworded", DAY, parts=["1.2"])
    assert revised_codes(latest) == []


def revised_after_a_pass(project: Workspace) -> None:
    """Items 1.1 and 1.2 ticked and self-reviewed, then 1.2 revised and accepted again."""
    built(project)
    lifecycle.self_review(project.root, NAME, "fine", DAY)
    project.replace(TASKS_FILE, "the help text names the limit", "the help names the limit")
    lifecycle.revise(project.root, NAME, "reworded", DAY, parts=["1.2"])
    lifecycle.accept(project.root, NAME, DAY)


def test_scenario_revised_item_is_the_next_step(latest: Workspace) -> None:
    """Requirement "Revised item reopened before review": wm asks for the reopen first."""
    from waymark.services.instructions import instructions  # noqa: PLC0415

    revised_after_a_pass(latest)
    step = instructions(latest.record(), None, NAME)
    assert (step["step"], step["item"]) == ("apply", "1.2")
    assert step["commands"][0] == (f'wm reopen {NAME} 1.2 --reason "<what the revision changed>"')
    lifecycle.reopen(latest.root, NAME, "1.2", DAY, reason="reworded")
    lifecycle.tick(latest.root, NAME, "1.2", DAY)
    assert latest.change_state().next_step.kind is StepKind.REVIEW


def test_scenario_archive_refused_for_a_revised_item(latest: Workspace) -> None:
    """Requirement "Revised item reopened before review": the archive can't pass it, even
    with an override."""
    revised_after_a_pass(latest)
    before = latest.read(TASKS_FILE)
    with pytest.raises(Refusal, match=r"item 1\.2 was revised") as refusal:
        lifecycle.archive(latest.root, NAME, DAY, built="Done.", override="looks fine")
    assert "wm reopen" in str(refusal.value)
    assert latest.read(TASKS_FILE) == before

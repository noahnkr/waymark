"""Requirements "Roadmap changed through wm" and "Milestone log": the wm roadmap commands."""

import datetime

import pytest

from tests.support import Workspace, milestone, proposal
from waymark.record.milestones import parse_milestone
from waymark.record.text import Document
from waymark.services import roadmap
from waymark.services.common import Refusal

DAY = datetime.date(2026, 11, 20)
FILE = "milestones/faster-search/milestone.md"


def lines(project: Workspace) -> list[str]:
    _, parsed = parse_milestone(Document.parse(FILE, project.read(FILE)))
    return [entry.text for entry in parsed.entries]


def log(project: Workspace) -> list[str]:
    text = project.read(FILE)
    return [line[2:] for line in text.split("## Log\n\n", 1)[1].splitlines() if line]


def refused(project: Workspace, action: str, *arguments: object, **options: object) -> str:
    before = project.read(FILE)
    with pytest.raises(Refusal) as refusal:
        getattr(roadmap, action)(project.root, *arguments, **options)
    assert project.read(FILE) == before
    return str(refusal.value)


def test_scenario_line_added(project: Workspace) -> None:
    project.write(FILE, milestone("- [add-limit](../../changes/add-limit/proposal.md)\n"))
    done = roadmap.add(project.root, "faster-search", "add-cache", "cache hot queries", DAY)
    assert done.paths == (FILE,)
    assert lines(project) == [
        "[add-limit](../../changes/add-limit/proposal.md)",
        "add-cache: cache hot queries",
    ]


def test_a_line_is_added_to_an_empty_roadmap(project: Workspace) -> None:
    project.write(FILE, milestone())
    roadmap.add(project.root, "faster-search", "add-cache", "cache hot queries", DAY)
    assert "## Roadmap\n\n- add-cache: cache hot queries\n\n## Log\n\n" in project.read(FILE)


def test_scenario_line_moved(project: Workspace) -> None:
    project.write(FILE, milestone("- add-limit: cap\n- add-cache: cache\n- add-index: index\n"))
    roadmap.move(project.root, "faster-search", "add-index", DAY, after="add-limit")
    roadmap.move(project.root, "faster-search", "add-cache", DAY)
    assert lines(project) == ["add-cache: cache", "add-limit: cap", "add-index: index"]
    roadmap.move(project.root, "faster-search", "add-cache", DAY, after="add-index")
    assert lines(project) == ["add-limit: cap", "add-index: index", "add-cache: cache"]


def test_scenario_planned_line_dropped(project: Workspace) -> None:
    project.write(FILE, milestone("- add-cache: cache hot queries\n- add-index: index\n"))
    roadmap.drop(project.root, "faster-search", "add-cache", "the index is fast enough", DAY)
    assert lines(project) == ["add-index: index"]


def test_scenario_active_member_not_dropped(project: Workspace) -> None:
    project.change(
        proposal_text=proposal().replace(
            "- Owner: Sam Doe\n", "- Owner: Sam Doe\n- Milestone: faster-search\n"
        )
    )
    project.write(FILE, milestone("- [add-limit](../../changes/add-limit/proposal.md): cap\n"))
    message = refused(project, "drop", "faster-search", "add-limit", "later", DAY)
    assert '"- Milestone:"' in message


def test_an_archived_or_unknown_change_line_may_be_dropped(project: Workspace) -> None:
    project.write(FILE, milestone("- [add-old](../../changes/add-old/proposal.md): gone\n"))
    roadmap.drop(project.root, "faster-search", "add-old", "it was deleted", DAY)
    assert lines(project) == []


def test_scenario_log_of_a_plans_changes(project: Workspace) -> None:
    project.write(FILE, milestone())
    roadmap.add(project.root, "faster-search", "add-cache", "cache hot queries", DAY, by="Ada")
    roadmap.move(project.root, "faster-search", "add-cache", DAY, by="Ada")
    roadmap.drop(
        project.root, "faster-search", "add-cache", "the index is fast enough", DAY, by="Ada"
    )
    assert project.read(FILE).endswith("\n## Log\n\n" + "".join(f"- {r}\n" for r in log(project)))
    assert log(project) == [
        "(added) 2026-11-20 add-cache by Ada: cache hot queries",
        "(moved) 2026-11-20 add-cache first by Ada",
        "(dropped) 2026-11-20 add-cache by Ada: the index is fast enough",
    ]


def test_records_name_the_git_user_without_by(project: Workspace) -> None:
    project.write(FILE, milestone())
    roadmap.add(project.root, "faster-search", "add-cache", "cache", DAY)
    assert log(project) == ["(added) 2026-11-20 add-cache by Sam Doe: cache"]


def test_the_roadmap_keeps_its_line_endings(project: Workspace) -> None:
    project.write(FILE, milestone("- add-limit: cap\n- add-cache: cache\n").replace("\n", "\r\n"))
    roadmap.move(project.root, "faster-search", "add-cache", DAY)
    roadmap.add(project.root, "faster-search", "add-index", "index", DAY)
    text = project.read(FILE)
    assert "\n" not in text.replace("\r\n", "")
    assert "- add-cache: cache\r\n- add-limit: cap\r\n- add-index: index\r\n" in text


def test_the_commands_refuse_what_they_cannot_do(project: Workspace) -> None:
    project.write(FILE, milestone("- add-limit: cap\n"))
    assert "not an active milestone" in refused(project, "add", "slower", "add-x", "x", DAY)
    assert "not a valid change name" in refused(project, "add", "faster-search", "Add_X", "x", DAY)
    assert "already on the roadmap" in refused(
        project, "add", "faster-search", "add-limit", "x", DAY
    )
    assert "not on the roadmap" in refused(project, "drop", "faster-search", "add-x", "x", DAY)
    assert "not on the roadmap" in refused(project, "move", "faster-search", "add-x", DAY)
    assert "not on the roadmap" in refused(
        project, "move", "faster-search", "add-limit", DAY, after="add-x"
    )
    assert "after itself" in refused(
        project, "move", "faster-search", "add-limit", DAY, after="add-limit"
    )

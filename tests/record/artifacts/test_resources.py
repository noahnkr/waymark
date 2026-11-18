"""Requirements "Resource layout", "Resource kinds" and "Specs a resource serves"."""

import datetime

from tests.support import Workspace, requirement, spec
from waymark.record.artifacts.resources import parse_resource
from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import Document

PATH = "resources/stripe.md"
SECTIONS = (
    "## What it is\n\nPayments.\n\n"
    "## Access\n\nThe key is in the vault.\n\n"
    "## Interface\n\nNone.\n\n"
    "## Data\n\nCharges.\n\n"
    "## Configuration\n\n### dev\n\nTest mode.\n\n### prod\n\nLive mode.\n\n"
    "## Verification\n\nA test charge.\n"
)


def resource(
    *,
    kind: str = "service",
    serves: str = "none",
    status: str = "active",
    verified: str = "2026-11-17",
    sections: str = SECTIONS,
) -> str:
    return (
        f"# Stripe\n\n- Kind: {kind}\n- Serves: {serves}\n- Status: {status}\n"
        f"- Verified: {verified}\n\n{sections}"
    )


def problems_of(project: Workspace) -> list[Problem]:
    return [problem for problem in project.record().problems if problem.path == PATH]


def test_scenario_complete_resource(project: Workspace) -> None:
    project.write(PATH, resource())
    assert problems_of(project) == []
    found = project.record().resources["stripe"]
    assert (found.title, found.kind, found.serves, found.status) == (
        "Stripe",
        "service",
        (),
        "active",
    )
    assert found.verified == datetime.date(2026, 11, 17)
    assert found.sections["Interface"] == "None."
    assert [(heading.level, heading.title) for heading in found.outline] == [
        (2, "What it is"),
        (2, "Access"),
        (2, "Interface"),
        (2, "Data"),
        (2, "Configuration"),
        (3, "dev"),
        (3, "prod"),
        (2, "Verification"),
    ]
    assert found.doc.path in [doc.path for doc in project.record().documents()]


def test_scenario_missing_section(project: Workspace) -> None:
    project.write(PATH, resource(sections=SECTIONS.replace("## Data\n\nCharges.\n\n", "")))
    [problem] = problems_of(project)
    assert problem.code == "missing-section"
    assert "## Data" in problem.message


def test_a_missing_line_is_named() -> None:
    text = resource().replace("- Status: active\n", "")
    [problem] = parse_resource("stripe", Document.parse(PATH, text)).problems
    assert problem.code == "missing-line"
    assert '"- Status:"' in problem.message


def test_scenario_date_in_another_form(project: Workspace) -> None:
    project.write(PATH, resource(verified="last week"))
    [problem] = problems_of(project)
    assert (problem.code, problem.line) == ("invalid-date", 6)
    assert "YYYY-MM-DD" in problem.message


def test_an_impossible_date_is_reported() -> None:
    found = parse_resource("stripe", Document.parse(PATH, resource(verified="2026-13-40")))
    assert [problem.code for problem in found.problems] == ["invalid-date"]


def test_a_status_other_than_active_or_retired_is_reported() -> None:
    found = parse_resource("stripe", Document.parse(PATH, resource(status="paused")))
    [problem] = found.problems
    assert (problem.code, problem.line) == ("unknown-status", 5)
    assert "`active`" in problem.message
    assert "`retired`" in problem.message


def test_scenario_unknown_kind(project: Workspace) -> None:
    project.write(PATH, resource(kind="repository"))
    [problem] = problems_of(project)
    assert (problem.code, problem.line) == ("unknown-kind", 3)
    for kind in ("service", "platform", "account", "database", "dataset", "document"):
        assert f"`{kind}`" in problem.message


def test_scenario_unknown_spec(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement()))
    project.write("specs/export.md", spec(requirement()))
    project.write(PATH, resource(serves="search, billing"))
    [problem] = problems_of(project)
    assert (problem.code, problem.line) == ("unknown-spec", 4)
    assert '"billing"' in problem.message
    assert "export, search" in problem.message
    assert project.record().resources["stripe"].serves == ("search", "billing")

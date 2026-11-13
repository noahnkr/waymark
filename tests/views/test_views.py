"""The views: what each payload holds, that it matches its schema, and how it renders."""

import datetime
import json
import time
from typing import Any

import pytest

from tests.support import Workspace, delta, proposal, requirement, spec
from tests.views.validator import errors
from waymark import __version__
from waymark.record.terms import Verdict
from waymark.services import lifecycle
from waymark.services.common import Refusal
from waymark.views import payloads, render
from waymark.views.payloads import VERSIONS
from waymark.views.schemas import SCHEMAS
from waymark.views.style import Style

NOW = datetime.datetime(2026, 3, 1, 12, tzinfo=datetime.UTC)
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
GOAL = "# Faster\n\n## Goal\n\na\n\n## Done when\n\nb\n\n## Non-goals\n\nc\n"
PLAIN = Style(color=False, unicode=False)
FANCY = Style(color=True, unicode=True)


def valid(payload: dict[str, Any]) -> dict[str, Any]:
    """Check a payload against its schema, in both renderings, and hand it back."""
    name = payload["schema"].removeprefix("wm.")
    assert errors(render.public(payload), SCHEMAS[name]) == []
    assert json.loads(render.to_json(payload)) == render.public(payload)
    for style in (PLAIN, FANCY):
        assert render.to_text(payload, style)
    render.to_text(payload, PLAIN).encode("ascii")
    return payload


def busy(project: Workspace) -> Workspace:
    """A record with one of everything, and something of every kind waiting on the human."""
    project.write("specs/search.md", spec(requirement(), requirement("Empty query")))
    project.write("changes/archive/2026-01-20-add-index/proposal.md", proposal(outcome="Indexed."))
    project.write(
        "changes/archive/2026-01-20-add-index/specs/search.md", delta(added=(requirement(),))
    )
    project.change(
        "add-order",
        deltas={"search": delta(added=(requirement("Result order"),))},
        tasks=HEAD
        + "- [ ] 1.1 Sort it   `review: independent`\n  - Criteria: newest first\n"
        + "- [ ] 1.2 Explain it\n  - Criteria: documented\n"
        + "- [ ] 1.3 Announce it\n  - Criteria: posted\n"
        + "- [ ] 1.4 Translate it\n  - Criteria: two languages\n",
    )
    lifecycle.accept(project.root, "add-order", DAY)
    lifecycle.tick(project.root, "add-order", "1.1")
    lifecycle.verdict(project.root, "add-order", "1.1", Verdict.SPEC_GAP, "ties?", DAY)
    lifecycle.block(project.root, "add-order", "1.2", "waiting for the wording")
    lifecycle.report_gap(project.root, "add-order", "1.3", "which channel?")
    project.change(
        "fix-limit",
        deltas={"search": delta(modified=(requirement(scenario="Edge"),))},
        tasks=HEAD + "- [ ] 1.1 Fix it   `review: none`\n",
    )
    lifecycle.accept(project.root, "fix-limit", DAY)
    lifecycle.tick(project.root, "fix-limit", "1.1")
    project.change("add-paging", deltas={"search": delta(added=(requirement("Paging"),))})
    project.change("cut-noise", deltas={"search": delta(modified=(requirement("Gone"),))})
    project.write("milestones/faster-search/goal.md", GOAL)
    project.write(
        "milestones/faster-search/roadmap.md",
        "# Roadmap\n\n"
        "- [x] [Index](../../changes/archive/2026-01-20-add-index/proposal.md)\n"
        "- [ ] [Order](../../changes/add-order/proposal.md)\n- [ ] Caching\n",
    )
    project.write(
        "explorations/caching.md",
        "# Caching\n\n## Context\n\nSlow.\n\n## Questions\n\n- Where to cache?\n\n"
        "## Approaches\n\n## Conclusion\n\n## Related\n",
    )
    return project


def test_every_payload_names_its_schema_and_version(project: Workspace) -> None:
    record = busy(project).record()
    built = [
        payloads.status(record),
        payloads.inbox(record),
        payloads.check(record, NOW),
        payloads.ls(record, "change"),
        payloads.show(record, "add-order"),
        payloads.show(record, "search"),
        payloads.show(record, "faster-search"),
        payloads.show(record, "caching"),
    ]
    views = {
        name
        for name in VERSIONS
        if not name.startswith(("instructions", "context", "doctor", "pr"))
    }
    assert {payload["schema"].removeprefix("wm.") for payload in built} == views
    assert set(SCHEMAS) == set(VERSIONS)
    for payload in built:
        valid(payload)
        assert payload["version"] == VERSIONS[payload["schema"].removeprefix("wm.")]


def test_status_shows_changes_in_flight_with_phase_and_progress(project: Workspace) -> None:
    payload = valid(payloads.status(busy(project).record()))
    changes = {change["name"]: change for change in payload["changes"]}
    assert list(changes) == ["add-order", "add-paging", "cut-noise", "fix-limit"]
    assert (changes["add-order"]["phase"], changes["add-order"]["ticked"]) == ("applying", 1)
    assert changes["add-order"]["total"] == 4
    assert changes["fix-limit"]["phase"] == "applied"
    assert changes["fix-limit"]["next_step"] == {
        "kind": "archive",
        "item": None,
        "human": True,
        "reason": "",
    }
    assert changes["add-paging"]["next_step"]["kind"] == "accept"
    assert changes["cut-noise"]["next_step"]["kind"] == "resolve-conflict"
    assert payload["layout"] == "repo"
    assert payload["writable"]
    assert payload["wm_version"] == payload["pinned_version"] == __version__


def test_status_shows_milestones_archived_changes_and_what_needs_the_human(
    project: Workspace,
) -> None:
    payload = payloads.status(busy(project).record())
    assert payload["milestones"] == [
        {"name": "faster-search", "archived": 1, "total": 2, "planned": 1}
    ]
    assert payload["recently_archived"] == [{"name": "add-index", "date": "2026-01-20"}]
    assert payload["needs_human"] == len(payloads.inbox(project.record())["entries"]) == 7
    text = render.to_text(payload, PLAIN)
    assert "7 things need you: wm inbox" in text
    assert "add-order" in text
    assert "[##........] 1/4" in text
    assert "* archive (you)" in text


def test_status_of_an_empty_record_says_how_to_start(project: Workspace) -> None:
    payload = valid(payloads.status(project.record()))
    assert payload["changes"] == []
    text = render.to_text(payload, PLAIN)
    assert "wm new change <name>" in text
    assert "Nothing needs you." in text


def test_status_says_when_the_pinned_version_differs(project: Workspace) -> None:
    project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    payload = valid(payloads.status(project.record()))
    assert not payload["writable"]
    assert "pinned to 9.9.9" in render.to_text(payload, PLAIN)


def test_inbox_lists_everything_only_the_human_can_resolve(project: Workspace) -> None:
    payload = valid(payloads.inbox(busy(project).record()))
    found = [(e["kind"], e["change"] or e["exploration"], e["item"]) for e in payload["entries"]]
    assert found == [
        ("accept", "add-paging", None),
        ("spec-gap", "add-order", "1.1"),
        ("spec-gap", "add-order", "1.3"),
        ("blocked", "add-order", "1.2"),
        ("conflict", "cut-noise", None),
        ("archive", "fix-limit", None),
        ("question", "caching", None),
    ]
    commands = {entry["kind"]: entry["command"] for entry in payload["entries"]}
    assert commands["accept"] == "wm accept add-paging"
    assert commands["blocked"] == 'wm resolve add-order 1.2 "<what was decided>"'
    assert commands["archive"].startswith("wm archive fix-limit")
    assert commands["question"] is None
    text = render.to_text(payload, PLAIN)
    assert "-- To accept " in text
    assert "waiting for the wording" in text
    assert "- Where to cache?" in text


def test_inbox_lists_a_verdict_that_came_back_to_the_human(project: Workspace) -> None:
    project.change(tasks=HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n")
    lifecycle.accept(project.root, "add-limit", DAY)
    lifecycle.tick(project.root, "add-limit", "1.1")
    lifecycle.verdict(project.root, "add-limit", "1.1", Verdict.CHANGES, "one", DAY)
    assert payloads.inbox(project.record())["entries"] == []
    lifecycle.reopen(project.root, "add-limit", "1.1", DAY)
    lifecycle.tick(project.root, "add-limit", "1.1")
    lifecycle.verdict(project.root, "add-limit", "1.1", Verdict.CHANGES, "two", DAY)
    (entry,) = valid(payloads.inbox(project.record()))["entries"]
    assert (entry["kind"], entry["item"]) == ("verdict", "1.1")
    assert entry["summary"] == "a second review asked for changes: two"


def test_inbox_asks_to_accept_again_after_acceptance_was_withdrawn(project: Workspace) -> None:
    project.change()
    lifecycle.accept(project.root, "add-limit", DAY)
    project.replace("changes/add-limit/proposal.md", "Paging.", "Paging and sorting.")
    (entry,) = payloads.inbox(project.record())["entries"]
    assert entry["kind"] == "accept"
    assert entry["summary"].startswith("Accept again:")


def test_empty_inbox_says_nothing_needs_the_human(project: Workspace) -> None:
    payload = valid(payloads.inbox(project.record()))
    assert payload["entries"] == []
    assert render.to_text(payload, PLAIN) == "x Nothing needs you."


def test_show_change_holds_everything_about_it(project: Workspace) -> None:
    payload = valid(payloads.show(busy(project).record(), "add-order"))
    assert payload["path"] == "changes/add-order"
    assert payload["owner"] == "Sam Doe"
    assert payload["accepted"] == {"date": "2026-01-15", "by": "Sam Doe"}
    assert payload["state"]["phase"] == "applying"
    assert payload["proposal"]["Why"] == "Long result lists are slow."
    assert payload["deltas"] == [
        {"spec": "search", "added": ["Result order"], "modified": [], "removed": []}
    ]
    assert payload["design"] == {"decisions": ["Where to cut"]}
    items = {item["number"]: item for item in payload["items"]}
    assert items["1.1"]["level"] == "independent"
    assert items["1.1"]["records"] == [
        {"kind": "review", "date": "2026-01-15", "verdict": "spec-gap", "text": "ties?"}
    ]
    assert items["1.2"]["blocked"] == "waiting for the wording"
    assert items["1.3"]["spec_gap"] == "which channel?"
    assert items["1.3"]["needs_human"] == "the implementer found a spec gap: which channel?"
    text = render.to_text(payload, PLAIN)
    for expected in ("Change: add-order", "Owner: Sam Doe", "Blocked: waiting for the wording"):
        assert expected in text


def test_show_finds_an_archived_change_by_name_or_folder(project: Workspace) -> None:
    record = busy(project).record()
    by_name = valid(payloads.show(record, "add-index"))
    by_folder = payloads.show(record, "2026-01-20-add-index")
    assert by_name == by_folder
    assert by_name["archived_on"] == "2026-01-20"
    assert by_name["state"] is None
    assert by_name["outcome"] == "Indexed."
    assert "Archived on 2026-01-20" in render.to_text(by_name, PLAIN)


def test_show_spec_includes_pending_deltas_and_history(project: Workspace) -> None:
    payload = valid(payloads.show(busy(project).record(), "search"))
    assert [item["name"] for item in payload["requirements"]] == ["Result limit", "Empty query"]
    assert payload["requirements"][0]["scenarios"][0]["steps"][1] == {
        "keyword": "WHEN",
        "text": "a search runs",
    }
    assert [(d["change"], d["added"], d["modified"]) for d in payload["pending"]] == [
        ("add-order", ["Result order"], []),
        ("add-paging", ["Paging"], []),
        ("cut-noise", [], ["Gone"]),
        ("fix-limit", [], ["Result limit"]),
    ]
    assert payload["history"] == [
        {"date": "2026-01-20", "change": "add-index", "outcome": "Indexed."}
    ]
    text = render.to_text(payload, PLAIN)
    assert "Pending deltas from active changes" in text
    assert "fix-limit: modifies Result limit" in text


def test_show_milestone_and_exploration(project: Workspace) -> None:
    record = busy(project).record()
    milestone = valid(payloads.show(record, "faster-search"))
    assert [(line["change"], line["status"]) for line in milestone["lines"]] == [
        ("add-index", "archived"),
        ("add-order", "active"),
        (None, "planned"),
    ]
    assert (milestone["archived"], milestone["total"]) == (1, 2)
    exploration = valid(payloads.show(record, "caching"))
    assert exploration["status"] == "open"
    assert exploration["sections"]["Questions"] == "- Where to cache?"


def test_show_refuses_an_unknown_name_and_a_name_shared_by_two_kinds(project: Workspace) -> None:
    busy(project)
    project.write("explorations/search.md", project.read("explorations/caching.md"))
    record = project.record()
    with pytest.raises(Refusal, match="wm ls"):
        payloads.show(record, "no-such-thing")
    with pytest.raises(Refusal, match="--kind spec"):
        payloads.show(record, "search")
    assert payloads.show(record, "search", "exploration")["schema"] == "wm.show.exploration"
    with pytest.raises(Refusal, match='no milestone named "search"'):
        payloads.show(record, "search", "milestone")


def test_ls_gives_one_entry_per_thing_with_its_state(project: Workspace) -> None:
    record = busy(project).record()
    changes = valid(payloads.ls(record, "change"))
    assert [(e["name"], e["state"]) for e in changes["entries"]] == [
        ("add-order", "applying"),
        ("add-paging", "planned"),
        ("cut-noise", "planned"),
        ("fix-limit", "applied"),
    ]
    with_archive = valid(payloads.ls(record, "change", archived=True))
    assert with_archive["entries"][-1] == {
        "name": "add-index",
        "state": "archived",
        "detail": "2026-01-20",
    }
    assert valid(payloads.ls(record, "spec"))["entries"] == [
        {"name": "search", "state": "living", "detail": "2 requirements; 4 pending changes"}
    ]
    assert valid(payloads.ls(record, "milestone"))["entries"] == [
        {"name": "faster-search", "state": "open", "detail": "1/2 changes archived"}
    ]
    assert valid(payloads.ls(record, "exploration"))["entries"] == [
        {"name": "caching", "state": "open", "detail": ""}
    ]
    text = render.to_text(changes, PLAIN)
    assert text.split("\n")[0] == "add-order   applying  1/4 items; next: apply"
    assert render.to_text(payloads.ls(project.record(), "milestone"), PLAIN)


def test_ls_of_nothing_says_so(project: Workspace) -> None:
    assert render.to_text(valid(payloads.ls(project.record(), "spec")), PLAIN) == "No specs."


def test_check_payload_counts_errors_and_warnings(project: Workspace) -> None:
    payload = valid(payloads.check(busy(project).record(), NOW))
    assert (payload["errors"], payload["warnings"]) == (1, 1)
    assert [finding["code"] for finding in payload["findings"]] == ["conflict", "not-archived"]
    text = render.to_text(payload, PLAIN)
    assert text.endswith("1 error(s), 1 warning(s).")
    assert "error: changes/cut-noise: conflict:" in text


def test_json_is_never_styled_and_survives_any_console(project: Workspace) -> None:
    project.write("specs/search.md", spec(requirement(statement="Search SHALL match “café”.")))
    text = render.to_json(payloads.show(project.record(), "search"))
    assert "\x1b" not in text
    text.encode("ascii")
    assert json.loads(text)["requirements"][0]["statement"] == "Search SHALL match “café”."


def test_styled_text_uses_color_and_glyphs_only_when_the_style_allows(project: Workspace) -> None:
    payload = payloads.status(busy(project).record())
    plain = render.to_text(payload, PLAIN)
    fancy = render.to_text(payload, FANCY)
    assert "\x1b[" not in plain
    plain.encode("ascii")
    assert "\x1b[" in fancy
    assert "█" in fancy
    assert "→" in fancy


def test_views_are_the_same_on_every_machine(project: Workspace) -> None:
    busy(project)
    first = payloads.status(project.record())
    assert first == payloads.status(project.record())
    assert str(project.root) not in render.to_json(first)
    assert str(project.root) not in render.to_json(payloads.show(project.record(), "add-order"))


def test_views_answer_in_about_a_second_on_a_large_record(workspace: Workspace) -> None:
    """A record with a few hundred changes and specs, read without any cache."""
    for index in range(300):
        name = "".join(chr(ord("a") + int(digit)) for digit in f"{index:03d}")
        requirements = [requirement(f"Rule {letter}") for letter in "abcde"]
        workspace.write(f"specs/area-{name}.md", spec(*requirements, title=f"Area {name}"))
        folder = f"changes/archive/2025-{index % 12 + 1:02d}-15-add-{name}"
        workspace.write(f"{folder}/proposal.md", proposal(outcome="Done."))
        workspace.write(f"{folder}/specs/area-{name}.md", delta(added=(requirement(),)))
        workspace.write(f"{folder}/tasks.md", HEAD + "- [x] 1.1 Do it   `review: none`\n")
        if index < 20:
            workspace.change(
                f"fix-{name}",
                deltas={f"area-{name}": delta(modified=(requirement("Rule a"),))},
            )
    timings: list[float] = []
    for _ in range(3):
        start = time.perf_counter()
        record = workspace.record()
        status = payloads.status(record)
        payloads.inbox(record)
        render.to_text(status, PLAIN)
        timings.append(time.perf_counter() - start)
    assert len(status["changes"]) == 20
    assert len(record.archived_changes) == 300
    assert min(timings) < 1.5, f"status took {min(timings):.2f}s on a large record"

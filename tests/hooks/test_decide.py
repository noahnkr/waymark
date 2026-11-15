"""Hook decisions: every allow, refuse and evidence write, on wm's neutral events."""

import datetime
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, DESIGN, TASKS, Workspace, proposal
from waymark import assets
from waymark.hooks.decide import decide
from waymark.hooks.events import Decision, Event, EventKind, Replacement, Role
from waymark.services import lifecycle
from waymark.services.atlas import register

NAME = "add-limit"
FOLDER = f"changes/{NAME}"
TASKS_FILE = f"{FOLDER}/tasks.md"
DAY = datetime.date(2026, 1, 15)
HEAD = "# Tasks\n\n## 1. Limit\n\n"
ONE_ITEM = HEAD + "- [ ] 1.1 Cap it\n  - Criteria: fifty at most\n"
INDEPENDENT = proposal().replace("Owner: Sam Doe\n", "Owner: Sam Doe\nReview: independent\n")


def built_for_review(project: Workspace) -> Workspace:
    """An independently reviewed change with its one item ticked."""
    project.change(proposal_text=INDEPENDENT, tasks=ONE_ITEM)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    return project


@pytest.fixture
def accepted(project: Workspace) -> Workspace:
    project.change()
    lifecycle.accept(project.root, NAME, DAY)
    return project


def ask(project: Workspace, kind: EventKind, **fields: object) -> Decision:
    return decide(Event(kind, project.root, **fields), DAY)  # type: ignore[arg-type]


def delegate(project: Workspace, agent: str, prompt: str) -> Decision:
    return ask(project, EventKind.DELEGATE, agent=agent, prompt=prompt)


def edit(
    project: Workspace, relative: str, role: Role = Role.PLANNER, **fields: object
) -> Decision:
    return ask(project, EventKind.EDIT, role=role, path=project.path(relative), **fields)


def replace(
    project: Workspace, relative: str, old: str, new: str, role: Role = Role.PLANNER
) -> Decision:
    return edit(project, relative, role, replacements=(Replacement(old, new),))


def command(project: Workspace, text: str, role: Role = Role.PLANNER) -> Decision:
    return ask(project, EventKind.COMMAND, role=role, command=text)


def stop(
    project: Workspace, role: Role, message: str, retried: bool = False, agent_id: str = ""
) -> Decision:
    return ask(
        project,
        EventKind.AGENT_STOP,
        role=role,
        message=message,
        retried=retried,
        agent_id=agent_id,
    )


def handback(project: Workspace, role: Role, message: str, agent_id: str = "agent-1") -> Decision:
    return ask(project, EventKind.HANDBACK, role=role, message=message, agent_id=agent_id)


def markers(project: Workspace) -> list[str]:
    folder = project.root / ".git" / "waymark" / "agents"
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


def test_events_outside_a_waymark_project_are_allowed(tmp_path: Path) -> None:
    for kind in EventKind:
        event = Event(kind, tmp_path, Role.REVIEWER, command="wm accept x", path=tmp_path / "a")
        assert decide(event, DAY) == Decision()


def test_session_start_injects_the_status(accepted: Workspace) -> None:
    decision = ask(accepted, EventKind.SESSION_START)
    assert decision.allow
    assert "Changes in flight" in decision.context
    assert NAME in decision.context
    assert "wm inbox" in decision.context
    assert "\x1b[" not in decision.context


def test_delegation_must_name_exactly_one_change_and_item(accepted: Workspace) -> None:
    for prompt in (
        "",
        "add-limit",
        "Please build item 1.1 of add-limit",
        "add-limit 1.1 and be careful with the bound",
        "add-limit 1.1\n\nUse the helper in utils.py.",
        "add-limit 1.1 1.2",
    ):
        decision = delegate(accepted, assets.IMPLEMENTER, prompt)
        assert not decision.allow, prompt
        assert 'exactly "<change> <item>"' in decision.reason
    assert delegate(accepted, assets.IMPLEMENTER, "add-limit 1.1").allow
    assert delegate(accepted, assets.IMPLEMENTER, "  add-limit 1.1\n").allow


def test_delegation_of_an_unaccepted_change_is_refused(project: Workspace) -> None:
    project.change()
    decision = delegate(project, assets.IMPLEMENTER, "add-limit 1.1")
    assert not decision.allow
    assert "is not accepted" in decision.reason


def test_delegation_of_an_item_without_criteria_is_refused(accepted: Workspace) -> None:
    decision = delegate(accepted, assets.IMPLEMENTER, "add-limit 1.2")
    assert not decision.allow
    assert "has no criteria" in decision.reason


def test_delegation_is_refused_when_the_record_has_problems(project: Workspace) -> None:
    project.change(design=DESIGN.replace("after sorting.", "after [sorting](sort.md)."))
    lifecycle.accept(project.root, NAME, DAY)
    decision = delegate(project, assets.IMPLEMENTER, "add-limit 1.1")
    assert not decision.allow
    assert "sort.md" in decision.reason


def test_delegation_to_a_reviewer_needs_something_to_review(project: Workspace) -> None:
    project.change(proposal_text=INDEPENDENT)
    lifecycle.accept(project.root, NAME, DAY)
    lifecycle.tick(project.root, NAME, "1.1")
    assert "items still to build (1.2)" in delegate(project, assets.REVIEWER, "add-limit").reason
    lifecycle.tick(project.root, NAME, "1.2")
    assert delegate(project, assets.REVIEWER, "add-limit").allow


def test_reviewer_is_started_with_the_change_alone(project: Workspace) -> None:
    built_for_review(project)
    refused = delegate(project, assets.REVIEWER, "add-limit 1.1")
    assert not refused.allow
    assert 'exactly "<change>"' in refused.reason


def test_reviewer_is_not_started_below_independent(accepted: Workspace) -> None:
    lifecycle.tick(accepted.root, NAME, "1.1")
    lifecycle.tick(accepted.root, NAME, "1.2")
    assert "no reviewer is started" in delegate(accepted, assets.REVIEWER, "add-limit").reason


def test_delegation_of_an_unknown_change_or_item_is_refused(accepted: Workspace) -> None:
    assert "no active change" in delegate(accepted, assets.IMPLEMENTER, "add-order 1.1").reason
    assert "no item 9.9" in delegate(accepted, assets.IMPLEMENTER, "add-limit 9.9").reason
    assert "no active change" in delegate(accepted, assets.REVIEWER, "add-order").reason


def test_other_agents_are_not_wm_business(accepted: Workspace) -> None:
    assert delegate(accepted, "general-purpose", "do anything you like").allow


def test_reviewer_edits_nothing(accepted: Workspace) -> None:
    for path in (accepted.root / "src" / "app.py", accepted.path(TASKS_FILE)):
        decision = ask(accepted, EventKind.EDIT, role=Role.REVIEWER, path=path, content="x")
        assert not decision.allow
        assert "A reviewer edits nothing" in decision.reason


def test_implementer_may_edit_code(accepted: Workspace) -> None:
    path = accepted.root / "src" / "app.py"
    assert ask(accepted, EventKind.EDIT, role=Role.IMPLEMENTER, path=path, content="x = 1\n").allow


def test_implementer_may_add_notes_under_an_item(accepted: Workspace) -> None:
    decision = replace(
        accepted,
        TASKS_FILE,
        "fifty-one matches\n",
        "fifty-one matches\n  - Note: the cap sits after sorting\n",
        Role.IMPLEMENTER,
    )
    assert decision.allow


def test_implementer_may_not_edit_any_other_record_file(accepted: Workspace) -> None:
    for relative in (f"{FOLDER}/proposal.md", f"{FOLDER}/design.md", "charter.md"):
        decision = edit(accepted, relative, Role.IMPLEMENTER, content="# changed\n")
        assert not decision.allow, relative
        assert "An implementer may add" in decision.reason


def test_implementer_may_not_change_the_task_list_beyond_notes(accepted: Workspace) -> None:
    for old, new in (
        ("Criteria: at most fifty", "Criteria: at most sixty"),
        ("- [ ] 1.1", "- [x] 1.1"),
        ("  - Verify: a test covers fifty-one matches\n", ""),
    ):
        assert not replace(accepted, TASKS_FILE, old, new, Role.IMPLEMENTER).allow, old


def test_specs_are_never_edited_by_an_agent(accepted: Workspace) -> None:
    for role in (Role.PLANNER, Role.IMPLEMENTER):
        decision = edit(accepted, "specs/search.md", role, content="# Search\n")
        assert not decision.allow
        assert "Write a delta" in decision.reason or "An implementer" in decision.reason
    assert "Specs are never edited by hand" in edit(accepted, "specs/x.md", content="x").reason


@pytest.fixture
def atlas(tmp_path: Path) -> Workspace:
    """An atlas whose accepted change builds item 1.1 in the repo api next, and 1.2 in web."""
    suite = Workspace(tmp_path / "atlas", ATLAS_CONFIG.replace('"some-tool"', '"claude-code"'))
    for root in (suite.root, tmp_path / "suite-api", tmp_path / "web"):
        git_init(root)
    register(suite.root, "web", "../web")
    suite.change(
        tasks=HEAD
        + "- [ ] 1.1 Add the endpoint\n  - Criteria: fifty at most\n  - Repo: api\n"
        + "- [ ] 1.2 Show the list\n  - Criteria: fifty rows\n  - Repo: web\n",
        design=DESIGN,
    )
    lifecycle.accept(suite.root, NAME, DAY)
    return suite


def test_planner_may_edit_the_repo_of_the_item_being_built(atlas: Workspace) -> None:
    path = atlas.root.parent / "suite-api" / "src" / "app.py"
    assert ask(atlas, EventKind.EDIT, role=Role.PLANNER, path=path, content="x").allow


def test_planner_edit_in_another_repo_names_the_repo_it_may_edit(atlas: Workspace) -> None:
    path = atlas.root.parent / "web" / "page.html"
    decision = ask(atlas, EventKind.EDIT, role=Role.PLANNER, path=path, content="x")
    assert not decision.allow
    assert '"api"' in decision.reason
    assert '"web"' in decision.reason
    assert f"{NAME} 1.1" in decision.reason


def test_planner_may_draft_and_revise_the_changes_content(accepted: Workspace) -> None:
    assert replace(accepted, f"{FOLDER}/proposal.md", "Paging.", "Paging and sorting.").allow
    assert replace(accepted, TASKS_FILE, "Cap the result count", "Cap the results").allow
    assert edit(accepted, TASKS_FILE, content=TASKS + "- [ ] 1.3 Announce it\n").allow
    assert edit(accepted, "charter.md", content="# New\n").allow
    assert edit(accepted, "changes/add-order/proposal.md", content=proposal()).allow


@pytest.mark.parametrize(
    ("old", "new", "what"),
    [
        ("- [ ] 1.1", "- [x] 1.1", "adds the tick on item 1.1"),
        (
            "fifty-one matches\n",
            "fifty-one matches\n  - (self-review) 2026-01-16: fine\n",
            'adds "(self-review) 2026-01-16: fine" under item 1.1',
        ),
        (
            "fifty-one matches\n",
            "fifty-one matches\n  - (review) 2026-01-16 pass: fine\n",
            "under item 1.1",
        ),
        (
            "1.2 Document the limit\n",
            "1.2 Document the limit\n  - Blocked: waiting\n",
            "under item 1.2",
        ),
        (
            "1.2 Document the limit\n",
            "1.2 Document the limit\n  - Spec gap: unclear\n",
            "under item 1.2",
        ),
        (
            "1.2 Document the limit\n",
            "1.2 Document the limit\n\n## Review\n\n- (self-review) 2026-01-16: fine\n",
            "in the Review section",
        ),
    ],
)
def test_agent_edit_that_adds_evidence_is_refused(
    accepted: Workspace, old: str, new: str, what: str
) -> None:
    decision = replace(accepted, TASKS_FILE, old, new)
    assert not decision.allow
    assert what in decision.reason
    assert "only wm writes evidence" in decision.reason


def test_agent_edit_that_removes_or_changes_evidence_is_refused(accepted: Workspace) -> None:
    lifecycle.tick(accepted.root, NAME, "1.1")
    lifecycle.tick(accepted.root, NAME, "1.2")
    lifecycle.self_review(accepted.root, NAME, "fine", DAY)
    assert (
        "removes the tick on item 1.1"
        in replace(accepted, TASKS_FILE, "- [x] 1.1", "- [ ] 1.1").reason
    )
    changed = replace(accepted, TASKS_FILE, "2026-01-15: fine", "2026-01-15: thoroughly checked")
    assert not changed.allow
    rewritten = edit(accepted, TASKS_FILE, content=TASKS)
    assert not rewritten.allow


def test_agent_may_not_write_the_acceptance_line(project: Workspace) -> None:
    project.change()
    line = "Accepted: 2026-01-15 by Sam Doe (fingerprint: 0123456789abcdef)"
    decision = replace(
        project, f"{FOLDER}/proposal.md", "Owner: Sam Doe\n", f"Owner: Sam Doe\n{line}\n"
    )
    assert not decision.allow
    assert 'adds the "Accepted:' in decision.reason
    whole = edit(project, f"{FOLDER}/proposal.md", content=proposal() + "\nSynced: 2026-01-15\n")
    assert not whole.allow


def test_edit_that_keeps_existing_evidence_is_allowed(accepted: Workspace) -> None:
    lifecycle.tick(accepted.root, NAME, "1.1")
    text = accepted.read(TASKS_FILE)
    assert edit(accepted, TASKS_FILE, content=text + "- [ ] 1.3 Announce it\n").allow


def test_edit_whose_result_cannot_be_known_is_left_to_the_tool(accepted: Workspace) -> None:
    assert replace(accepted, TASKS_FILE, "text that is not in the file", "- [x] 1.1").allow


def test_record_file_is_validated_after_an_edit(accepted: Workspace) -> None:
    path = accepted.path(f"{FOLDER}/specs/search.md")
    assert ask(accepted, EventKind.EDITED, path=path).allow
    accepted.replace(f"{FOLDER}/specs/search.md", "- WHEN a search runs\n", "")
    decision = ask(accepted, EventKind.EDITED, path=path)
    assert not decision.allow
    assert f"waymark/{FOLDER}/specs/search.md has 1 format problem" in decision.reason
    assert "WHEN" in decision.reason
    assert ask(accepted, EventKind.EDITED, path=accepted.root / "src" / "app.py").allow


def test_no_agent_may_run_wm_accept(accepted: Workspace) -> None:
    for role in Role:
        decision = command(accepted, "wm accept add-limit", role)
        assert not decision.allow
        assert "Only the human accepts a change" in decision.reason
    assert not command(accepted, "git status && uv run wm accept add-limit").allow


def test_no_agent_may_override_the_archive_gate(accepted: Workspace) -> None:
    for text in (
        'wm archive add-limit --outcome "x" --override "no time"',
        "wm archive add-limit --override=later",
    ):
        decision = command(accepted, text)
        assert not decision.allow
        assert "Only the human may archive past a missing review" in decision.reason


def test_planner_may_run_the_other_wm_commands(accepted: Workspace) -> None:
    for text in (
        "wm tick add-limit 1.1",
        'wm archive add-limit --outcome "done"',
        'wm review add-limit 1.1 --self "fine"',
        'git commit -m "feat: cap results"',
        "wm status",
    ):
        assert command(accepted, text).allow, text


@pytest.mark.parametrize("role", [Role.IMPLEMENTER, Role.REVIEWER])
def test_delegated_agents_run_no_writing_wm_commands(accepted: Workspace, role: Role) -> None:
    for text in ("wm tick add-limit 1.1", 'wm block add-limit 1.1 "x"', "wm new change add-x"):
        decision = command(accepted, text, role)
        assert not decision.allow, text
        assert "writes the record" in decision.reason
    for text in ("wm context add-limit 1.1 --for implement", "wm show add-limit", "wm status"):
        assert command(accepted, text, role).allow, text


@pytest.mark.parametrize("role", [Role.IMPLEMENTER, Role.REVIEWER])
def test_delegated_agents_do_not_commit_or_push(accepted: Workspace, role: Role) -> None:
    for text in ('git add -A && git commit -m "feat: x"', "git push origin add-limit"):
        decision = command(accepted, text, role)
        assert not decision.allow, text
        assert "The planner commits" in decision.reason


def test_implementer_may_change_state_but_reviewer_may_not(accepted: Workspace) -> None:
    for text in ("mkdir -p src/search", "pip install -e .", "echo x > src/a.py", "git stash"):
        assert command(accepted, text, Role.IMPLEMENTER).allow, text
        decision = command(accepted, text, Role.REVIEWER)
        assert not decision.allow, text
        assert "A reviewer runs read-only commands" in decision.reason
    for text in ("pytest -q", "git diff", "cat src/a.py", "wm show add-limit"):
        assert command(accepted, text, Role.REVIEWER).allow, text


def test_commit_that_is_not_conventional_is_refused(accepted: Workspace) -> None:
    decision = command(accepted, 'git commit -m "wip"')
    assert not decision.allow
    assert decision.reason.startswith('The commit was stopped: "wip" is not a conventional')
    assert "for example: fix: accept an empty search query" in decision.reason
    chained = command(accepted, 'git add -A && git commit --message="update stuff" && git push')
    assert "The commit was stopped" in chained.reason


def test_conventional_commit_is_allowed(accepted: Workspace) -> None:
    for text in (
        'git commit -m "fix: accept an empty search query"',
        'git add -A && git commit -m "feat: cap results" -m "Fifty at most."',
        'git -C src commit --message "docs(api): describe the limit"',
    ):
        assert command(accepted, text).allow, text


def test_commit_with_a_scope_the_settings_do_not_list_is_refused(project: Workspace) -> None:
    project.write("config.toml", CONFIG + 'commit_scopes = ["api", "docs"]\n')
    decision = command(project, 'git commit -m "feat(web): add a share button"')
    assert not decision.allow
    assert "The commit was stopped" in decision.reason
    assert "(api, docs)" in decision.reason
    assert command(project, 'git commit -m "feat(api): add a share button"').allow


def test_commit_message_from_a_here_document_is_checked(accepted: Workspace) -> None:
    heredoc = "git commit -m \"$(cat <<'EOF'\n{}\n\nMore words.\nEOF\n)\""
    decision = command(accepted, heredoc.format("wip"))
    assert not decision.allow
    assert "The commit was stopped" in decision.reason
    assert command(accepted, heredoc.format("feat: cap results")).allow


def test_commit_message_from_a_file_is_read_against_the_commands_folder(
    accepted: Workspace,
) -> None:
    (accepted.root / "message.txt").write_bytes(b"wip\n")
    (accepted.root / "good.txt").write_bytes(b"feat: cap results\r\n\r\nFifty at most.\r\n")
    decision = command(accepted, "git commit -F message.txt")
    assert not decision.allow
    assert "The commit was stopped" in decision.reason
    assert not command(accepted, f"git commit --file {accepted.root / 'message.txt'}").allow
    assert command(accepted, "git commit -F good.txt").allow
    assert command(accepted, "git commit -F missing.txt").allow


def test_commit_whose_message_cannot_be_read_is_allowed(accepted: Workspace) -> None:
    for text in (
        "git commit",
        "git commit --amend --no-edit",
        'git commit -m "$MESSAGE"',
        'git commit -m "$(git log -1 --format=%s)"',
        "git commit --fixup HEAD~1",
    ):
        assert command(accepted, text).allow, text


def test_delegated_agents_commit_refusal_keeps_its_wording(accepted: Workspace) -> None:
    for role in (Role.IMPLEMENTER, Role.REVIEWER):
        decision = command(accepted, 'git commit -m "wip"', role)
        assert not decision.allow
        assert "The planner commits" in decision.reason


def test_commit_outside_a_waymark_project_is_allowed(tmp_path: Path) -> None:
    event = Event(EventKind.COMMAND, tmp_path, Role.PLANNER, command='git commit -m "wip"')
    assert decide(event, DAY) == Decision()


def test_implementer_done_ticks_its_item(accepted: Workspace) -> None:
    decision = stop(
        accepted,
        Role.IMPLEMENTER,
        "Built the cap.\n\nITEM: add-limit 1.1\nRESULT: done: fifty-one matches return fifty",
    )
    assert decision.allow
    assert decision.notice == "Waymark: Ticked item 1.1 of add-limit."
    assert "- [x] 1.1 Cap the result count" in accepted.read(TASKS_FILE)
    assert accepted.record().problems == ()


def test_implementer_blocked_writes_the_blocked_line(accepted: Workspace) -> None:
    decision = stop(
        accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: blocked - the index is down"
    )
    assert decision.allow
    assert "  - Blocked: the index is down" in accepted.read(TASKS_FILE)
    assert "- [ ] 1.1" in accepted.read(TASKS_FILE)


def test_implementer_spec_gap_writes_the_spec_gap_line(accepted: Workspace) -> None:
    stop(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: spec-gap: empty query?")
    assert "  - Spec gap: empty query?" in accepted.read(TASKS_FILE)
    assert accepted.change_state().items[0].escalated is not None


def test_implementer_partial_leaves_a_note_and_the_item_unticked(accepted: Workspace) -> None:
    stop(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: partial: the test is missing")
    text = accepted.read(TASKS_FILE)
    assert "  - Note: partial: the test is missing" in text
    assert "- [ ] 1.1" in text
    assert accepted.change_state().next_step.item == "1.1"


def test_reviewer_verdict_is_written_from_its_own_words(project: Workspace) -> None:
    built_for_review(project)
    decision = stop(
        project,
        Role.REVIEWER,
        "I checked.\n\nFINDING: suggestion: docs/search.md: say the limit\n\n"
        "CHANGE: add-limit\nVERDICT: pass: boundary covered at 50 and 51",
    )
    assert decision.allow
    assert project.read(TASKS_FILE).endswith(
        "## Review\n\n- (review) 2026-01-15 pass: boundary covered at 50 and 51\n"
        "  - suggestion: docs/search.md: say the limit\n"
    )
    assert project.change_state().applied


def test_reviewer_changes_verdict_names_the_items_to_rebuild(project: Workspace) -> None:
    built_for_review(project)
    stop(
        project,
        Role.REVIEWER,
        "FINDING: critical: src/search.py:12: fifty-one come back\n"
        "CHANGE: add-limit\nVERDICT: changes 1.1: off by one at 50",
    )
    text = project.read(TASKS_FILE)
    assert "- (review) 2026-01-15 changes 1.1: off by one at 50" in text
    assert "  - critical: src/search.py:12: fifty-one come back" in text
    assert project.change_state().review.reopen == ("1.1",)


def test_reviewer_finding_that_cannot_be_read_is_refused(project: Workspace) -> None:
    built_for_review(project)
    before = project.read(TASKS_FILE)
    decision = stop(
        project, Role.REVIEWER, "FINDING: looks odd\nCHANGE: add-limit\nVERDICT: pass: fine"
    )
    assert not decision.allow
    assert '"FINDING: looks odd"' in decision.reason
    assert project.read(TASKS_FILE) == before


@pytest.mark.parametrize(
    "message",
    [
        "All done, the tests pass.",
        "RESULT: done: built it",
        "ITEM: add-limit 1.1",
        "ITEM: add-limit 1.1\nVERDICT: pass: looks good",
        "ITEM: add-limit\nRESULT: done",
        "item add-limit 1.1 result done",
    ],
)
def test_implementer_must_end_with_its_item_and_result(accepted: Workspace, message: str) -> None:
    before = accepted.read(TASKS_FILE)
    decision = stop(accepted, Role.IMPLEMENTER, message)
    assert not decision.allow
    assert '"ITEM: <change> <item>"' in decision.reason
    assert "RESULT: done | partial | spec-gap | blocked" in decision.reason
    assert accepted.read(TASKS_FILE) == before


def test_reviewer_must_end_with_its_change_and_verdict(accepted: Workspace) -> None:
    for message in ("ITEM: add-limit 1.1\nRESULT: done", "ITEM: add-limit 1.1\nVERDICT: pass: ok"):
        decision = stop(accepted, Role.REVIEWER, message)
        assert not decision.allow
        assert '"CHANGE: <change>"' in decision.reason
        assert "VERDICT: pass | changes <item> <item>... | spec-gap" in decision.reason


def test_ending_that_cannot_be_recorded_keeps_the_agent_going(accepted: Workspace) -> None:
    wrong_item = stop(accepted, Role.IMPLEMENTER, "ITEM: add-limit 9.9\nRESULT: done: ok")
    assert not wrong_item.allow
    assert "no item 9.9" in wrong_item.reason
    no_note = stop(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: blocked")
    assert not no_note.allow
    assert "Give a reason" in no_note.reason


def test_agent_asked_once_already_is_let_go_with_a_notice(accepted: Workspace) -> None:
    before = accepted.read(TASKS_FILE)
    decision = stop(accepted, Role.IMPLEMENTER, "I am finished.", retried=True)
    assert decision.allow
    assert "recorded nothing for the implementer" in decision.notice
    assert accepted.read(TASKS_FILE) == before


def test_last_ending_in_the_message_is_the_one_recorded(accepted: Workspace) -> None:
    message = (
        "Earlier I thought:\nITEM: add-limit 1.2\nRESULT: blocked: unsure\n\n"
        "After checking:\nITEM: add-limit 1.1\nRESULT: done: verified"
    )
    stop(accepted, Role.IMPLEMENTER, message)
    text = accepted.read(TASKS_FILE)
    assert "- [x] 1.1" in text
    assert "Blocked:" not in text


def test_main_session_stopping_is_not_wm_business(accepted: Workspace) -> None:
    assert stop(accepted, Role.PLANNER, "nothing special") == Decision()


def test_implementer_done_in_the_foreground_ticks_the_item(accepted: Workspace) -> None:
    decision = stop(
        accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: done: built", agent_id="a1"
    )
    assert decision.allow
    assert "- [x] 1.1" in accepted.read(TASKS_FILE)
    assert markers(accepted) == []


def test_implementer_in_the_background_ticks_the_item(accepted: Workspace) -> None:
    decision = handback(
        accepted, Role.IMPLEMENTER, "Built it.\n\nITEM: add-limit 1.1\nRESULT: done: built"
    )
    assert decision.allow
    assert decision.notice.startswith("Waymark: ")
    assert "- [x] 1.1" in accepted.read(TASKS_FILE)
    assert markers(accepted) == ["agent-1"]


def test_handback_records_every_result_as_a_final_message_would(accepted: Workspace) -> None:
    handback(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: blocked: no database")
    assert "  - Blocked: no database" in accepted.read(TASKS_FILE)


def test_reviewer_in_the_background(project: Workspace) -> None:
    built_for_review(project)
    decision = handback(
        project, Role.REVIEWER, "CHANGE: add-limit\nVERDICT: pass: boundary covered at 50"
    )
    assert decision.allow
    assert "- (review) 2026-01-15 pass: boundary covered at 50" in project.read(TASKS_FILE)
    assert project.change_state().applied


def test_report_without_an_ending_is_refused(accepted: Workspace) -> None:
    before = accepted.read(TASKS_FILE)
    decision = handback(accepted, Role.IMPLEMENTER, "All done, the tests pass.")
    assert not decision.allow
    assert '"ITEM: <change> <item>"' in decision.reason
    assert "RESULT: done | partial | spec-gap | blocked" in decision.reason
    assert accepted.read(TASKS_FILE) == before


def test_reviewer_report_without_a_verdict_is_refused(accepted: Workspace) -> None:
    decision = handback(accepted, Role.REVIEWER, "CHANGE: add-limit\nRESULT: done")
    assert not decision.allow
    assert "VERDICT: pass | changes <item> <item>... | spec-gap" in decision.reason


def test_second_report_without_an_ending_is_let_through_with_a_notice(accepted: Workspace) -> None:
    before = accepted.read(TASKS_FILE)
    assert not handback(accepted, Role.IMPLEMENTER, "Finished.").allow
    decision = handback(accepted, Role.IMPLEMENTER, "Finished, really.")
    assert decision.allow
    assert "recorded nothing for the implementer" in decision.notice
    assert "wm commands" in decision.notice
    assert accepted.read(TASKS_FILE) == before
    after = stop(accepted, Role.IMPLEMENTER, "Bye.", agent_id="agent-1")
    assert after == Decision()
    assert markers(accepted) == []


def test_report_refused_once_then_fixed_is_recorded(accepted: Workspace) -> None:
    assert not handback(accepted, Role.IMPLEMENTER, "Finished.").allow
    assert handback(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: done: ok").allow
    assert "- [x] 1.1" in accepted.read(TASKS_FILE)


def test_stop_after_a_recorded_handback_is_allowed_without_an_ending(accepted: Workspace) -> None:
    handback(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: done: built")
    after = accepted.read(TASKS_FILE)
    decision = stop(accepted, Role.IMPLEMENTER, "Report handed back.", agent_id="agent-1")
    assert decision == Decision()
    assert accepted.read(TASKS_FILE) == after
    assert markers(accepted) == []


def test_stop_of_another_agent_still_needs_its_ending(accepted: Workspace) -> None:
    handback(accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: done: built")
    decision = stop(accepted, Role.IMPLEMENTER, "Report handed back.", agent_id="agent-2")
    assert not decision.allow
    assert markers(accepted) == ["agent-1"]


def test_stop_after_one_refused_handback_still_needs_its_ending(accepted: Workspace) -> None:
    handback(accepted, Role.IMPLEMENTER, "Finished.")
    assert not stop(accepted, Role.IMPLEMENTER, "Bye.", agent_id="agent-1").allow
    decision = stop(
        accepted, Role.IMPLEMENTER, "ITEM: add-limit 1.1\nRESULT: done: ok", agent_id="agent-1"
    )
    assert decision.allow
    assert "- [x] 1.1" in accepted.read(TASKS_FILE)
    assert markers(accepted) == []


def test_main_session_handing_back_is_not_wm_business(accepted: Workspace) -> None:
    before = accepted.read(TASKS_FILE)
    assert handback(accepted, Role.PLANNER, "nothing special") == Decision()
    assert accepted.read(TASKS_FILE) == before
    assert markers(accepted) == []

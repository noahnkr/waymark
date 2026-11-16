"""The migration to record format 2: every change, active and archived, in records."""

import datetime

from tests.support import TASKS, Workspace, proposal
from waymark.record.files import RecordFiles
from waymark.record.record import load_archived_change
from waymark.record.state import AcceptanceState
from waymark.services.migrations import migrate

ACTIVE = "changes/add-limit"
ARCHIVED = "changes/archive/2026-01-20-old-limit"
ACCEPTED = "Accepted: 2026-01-15 by Sam Doe (fingerprint: 0123456789abcdef; items: 1.1 1.2)"
OLD_TASKS = """# Tasks

## 1. Limit

- [x] 1.1 Cap it   `review: independent`   `build: delegate`
  - Criteria: fifty at most
  - (review) 2026-01-19 pass: boundary covered
  - (self-review) 2026-01-19: fine
  - Note: took the long way
    round the cache

## Review

- (review) 2026-01-20 pass: fine
  - suggestion: docs/search.md: say the limit
"""


def at_format_1(workspace: Workspace) -> Workspace:
    workspace.replace("config.toml", "record_format = 2", "record_format = 1")
    return workspace


def migrated(workspace: Workspace) -> tuple[str, ...]:
    return migrate(RecordFiles(workspace.path("")))


def test_scenario_accepted_change_migrated(workspace: Workspace) -> None:
    at_format_1(workspace)
    text = proposal().replace(
        "Owner: Sam Doe\n", f"Owner: Sam Doe\n{ACCEPTED}\nSynced: 2026-01-16\n"
    )
    blocked = TASKS.replace(
        "- [ ] 1.2 Document the limit\n", "- [ ] 1.2 Document the limit\n  - Blocked: the key\n"
    )
    workspace.change(proposal_text=text, tasks=blocked)
    assert migrated(workspace) == (
        "format 1 to 2: wm's lines in every change became dated records, kept in each task "
        "list's Log",
    )
    assert workspace.read(f"{ACTIVE}/proposal.md") == proposal()
    today = datetime.date.today().isoformat()
    tasks = workspace.read(f"{ACTIVE}/tasks.md")
    assert f"- [ ] 1.2 Document the limit\n  - (blocked) {today}: the key\n" in tasks
    assert tasks.endswith(
        "\n## Log\n\n"
        "- (accepted) 2026-01-15 fingerprint 0123456789abcdef items 1.1 1.2 by Sam Doe\n"
        "- (synced) 2026-01-16\n"
    )
    assert "record_format = 2" in workspace.read("config.toml")
    change = workspace.record().changes["add-limit"]
    assert change.problems == ()
    assert change.acceptance is not None
    assert workspace.change_state().acceptance is AcceptanceState.WITHDRAWN


def test_scenario_archived_change_migrated(workspace: Workspace) -> None:
    at_format_1(workspace)
    old_acceptance = "Accepted: 2026-01-15 by Sam Doe (fingerprint: 0123456789abcdef)"
    outcome = "Shipped.\n\nReview override: reviewed by hand"
    workspace.write(
        f"{ARCHIVED}/proposal.md",
        proposal(outcome=outcome).replace(
            "Owner: Sam Doe\n", f"Owner: Sam Doe\n{old_acceptance}\n"
        ),
    )
    workspace.write(f"{ARCHIVED}/tasks.md", OLD_TASKS)
    migrated(workspace)
    assert workspace.read(f"{ARCHIVED}/proposal.md") == proposal(outcome="Shipped.")
    assert workspace.read(f"{ARCHIVED}/tasks.md") == (
        "# Tasks\n\n## 1. Limit\n\n"
        "- [x] 1.1 Cap it   `build: delegate`\n"
        "  - Criteria: fifty at most\n"
        "  - (note) 2026-01-19: review pass: boundary covered\n"
        "  - (note) 2026-01-19: self-review: fine\n"
        f"  - (note) {datetime.date.today().isoformat()}: took the long way round the cache\n"
        "\n## Log\n\n"
        "- (accepted) 2026-01-15 fingerprint 0123456789abcdef items 1.1 by Sam Doe\n"
        "- (review) 2026-01-20 pass: fine\n"
        "  - suggestion `docs/search.md`: say the limit\n"
        "- (override) 2026-01-20: reviewed by hand\n"
    )
    record = workspace.record()
    change = load_archived_change(record, record.archived_changes[0])
    assert change.problems == ()
    assert change.tasks is not None
    assert change.tasks.items[0].delegate


def test_a_record_already_in_format_2_is_not_migrated(workspace: Workspace) -> None:
    workspace.change()
    before = workspace.read(f"{ACTIVE}/tasks.md")
    assert migrated(workspace) == ()
    assert workspace.read(f"{ACTIVE}/tasks.md") == before


def test_windows_line_endings_are_kept(workspace: Workspace) -> None:
    at_format_1(workspace)
    text = proposal().replace("Owner: Sam Doe\n", f"Owner: Sam Doe\n{ACCEPTED}\n")
    workspace.change(proposal_text=text.replace("\n", "\r\n"), tasks=TASKS.replace("\n", "\r\n"))
    migrated(workspace)
    for name in ("proposal.md", "tasks.md"):
        written = workspace.read(f"{ACTIVE}/{name}")
        assert "\n" not in written.replace("\r\n", "")
    assert "\r\n## Log\r\n\r\n- (accepted) " in workspace.read(f"{ACTIVE}/tasks.md")

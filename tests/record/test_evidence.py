"""Evidence in a task list: every tick and every record, and nothing a human writes."""

from tests.support import TASKS
from waymark.record.evidence import evidence, evidence_changes

PATH = "changes/add-limit/tasks.md"
LOGGED = TASKS + (
    "\n## Log\n\n"
    "- (accepted) 2026-01-15 fingerprint 0123456789abcdef items 1.1 1.2 by Sam Doe\n"
    "- (review) 2026-01-16 pass by wm-reviewer: fine\n"
    "  - suggestion `docs/search.md`: say the limit\n"
)


def test_records_and_ticks_are_evidence() -> None:
    text = LOGGED.replace("- [ ] 1.1", "- [x] 1.1").replace(
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n",
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n"
        "  - (blocked) 2026-01-16 by Sam Doe: the key\n",
    )
    found = evidence(PATH, text)
    assert found["the tick on item 1.1"] == 1
    assert found['"(blocked) 2026-01-16 by Sam Doe: the key" under item 1.2'] == 1
    assert sum(1 for name in found if name.endswith("in the Log section")) == 3


def test_what_a_human_writes_is_not_evidence() -> None:
    edited = LOGGED.replace("at most fifty results", "at most sixty results")
    assert evidence_changes(PATH, LOGGED, edited) == []
    added = LOGGED.replace(
        "\n## Log\n", "- [ ] 1.3 Announce it\n  - Criteria: done\n  - Verify: a test\n\n## Log\n"
    )
    assert evidence_changes(PATH, LOGGED, added) == []


def test_changing_a_record_is_reported_both_ways() -> None:
    changed = LOGGED.replace("by wm-reviewer: fine", "by wm-reviewer: thorough")
    reported = evidence_changes(PATH, LOGGED, changed)
    assert any(line.startswith("adds ") for line in reported)
    assert any(line.startswith("removes ") for line in reported)


def test_other_files_hold_no_evidence() -> None:
    assert evidence("changes/add-limit/proposal.md", "Accepted: 2026-01-15 by Sam Doe\n") == {}

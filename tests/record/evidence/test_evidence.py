"""Evidence in a task list: every tick and every record, and nothing a human writes."""

from tests.support import TASKS, milestone
from waymark.record.evidence.evidence import evidence, evidence_changes

PATH = "changes/add-limit/tasks.md"
LOGGED = TASKS + (
    "\n## Log\n\n"
    "- 2026-01-15 (accepted) fingerprint 0123456789abcdef items 1.1, 1.2 by Sam Doe\n"
    "- 2026-01-16 (review) pass by wm-reviewer: fine\n"
    "  - [suggestion] `docs/search.md`: say the limit\n"
)


def test_records_and_ticks_are_evidence() -> None:
    text = LOGGED.replace("- [ ] 1.1", "- [x] 1.1").replace(
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n",
        "- [ ] 1.2 Document the limit\n"
        "  - Criteria: the help text names the limit\n"
        "  - Verify: read the help text\n"
        "  - 2026-01-16 (blocked) by Sam Doe: the key\n",
    )
    found = evidence(PATH, text)
    assert found["the tick on item 1.1"] == 1
    assert found['"2026-01-16 (blocked) by Sam Doe: the key" under item 1.2'] == 1
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


MILESTONE_PATH = "milestones/faster-search/milestone.md"
PLANNED = milestone(
    "<!-- one line per change -->\n- add-limit: cap\n- [x] [add-index](../x/proposal.md)\n"
) + ("\n## Log\n\n- 2026-11-20 (added) add-limit by Ada: cap\n")


def test_roadmap_lines_and_the_milestone_log_are_evidence() -> None:
    found = evidence(MILESTONE_PATH, PLANNED)
    assert found['the roadmap line "add-limit: cap"'] == 1
    assert found['the roadmap line "[x] [add-index](../x/proposal.md)"'] == 1
    assert found['"- 2026-11-20 (added) add-limit by Ada: cap" in the milestone\'s Log'] == 1
    assert len(found) == 3


def test_editing_a_milestone_goal_changes_no_evidence() -> None:
    edited = PLANNED.replace("Answers in a blink.", "Answers in a blink, every time.")
    assert evidence_changes(MILESTONE_PATH, PLANNED, edited) == []


def test_adding_or_rewording_a_roadmap_line_changes_evidence() -> None:
    added = PLANNED.replace("- add-limit: cap\n", "- add-limit: cap\n- add-cache: cache\n")
    assert evidence_changes(MILESTONE_PATH, PLANNED, added) == [
        'adds the roadmap line "add-cache: cache"'
    ]
    reworded = PLANNED.replace("- add-limit: cap\n", "- add-limit: cap the results\n")
    assert len(evidence_changes(MILESTONE_PATH, PLANNED, reworded)) == 2


def test_an_archived_milestone_has_no_evidence() -> None:
    assert evidence("milestones/archive/2026-01-01-faster-search/milestone.md", PLANNED) == {}


def test_records_in_the_old_shape_are_evidence_too() -> None:
    text = TASKS.replace(
        "  - Verify: read the help text\n",
        "  - Verify: read the help text\n  - (blocked) 2026-01-16 by Sam Doe: the key\n",
    )
    found = evidence(PATH, text)
    assert found['"(blocked) 2026-01-16 by Sam Doe: the key" under item 1.2'] == 1

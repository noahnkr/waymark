"""The migration framework: one format step at a time, each applied whole or not at all."""

import pytest

from tests.support import Workspace, spec
from waymark.record.config import RECORD_FORMAT
from waymark.record.edits import set_record_format
from waymark.record.files import RecordFiles
from waymark.record.store import Transaction
from waymark.services.common import Refusal
from waymark.services.migrations import MIGRATIONS, Migration, migrate, pending, stored_format


def rename_purpose(files: RecordFiles, transaction: Transaction) -> None:
    for entry in files.entries("specs"):
        path = f"specs/{entry.name}"
        text = files.read(path, []) or ""
        transaction.write(path, text.replace("## Purpose", "## Aim"))


def add_marker(files: RecordFiles, transaction: Transaction) -> None:
    transaction.write("charter.md", (files.read("charter.md", []) or "") + "\nMigrated.\n")


def break_things(files: RecordFiles, transaction: Transaction) -> None:
    transaction.write("charter.md", "half done\n")
    transaction.write("config.toml/not-a-folder.md", "this write can't succeed\n")


ONE_TO_TWO = Migration(1, "rename the purpose section", rename_purpose)
TWO_TO_THREE = Migration(2, "mark the charter", add_marker)
BROKEN = Migration(2, "fail halfway", break_things)


def files_of(workspace: Workspace) -> RecordFiles:
    return RecordFiles(workspace.path(""))


def test_this_version_has_a_migration_for_every_earlier_format() -> None:
    assert [migration.source for migration in MIGRATIONS] == list(range(1, RECORD_FORMAT))
    assert pending(RECORD_FORMAT) == ()


def test_record_in_the_current_format_needs_no_migration(workspace: Workspace) -> None:
    before = workspace.read("config.toml")
    assert migrate(files_of(workspace)) == ()
    assert workspace.read("config.toml") == before


def test_migrations_run_in_order_and_advance_the_format_number(workspace: Workspace) -> None:
    workspace.write("specs/search.md", spec())
    done = migrate(files_of(workspace), [TWO_TO_THREE, ONE_TO_TWO], target=3)
    assert done == (
        "format 1 to 2: rename the purpose section",
        "format 2 to 3: mark the charter",
    )
    assert "## Aim" in workspace.read("specs/search.md")
    assert workspace.read("charter.md").endswith("\nMigrated.\n")
    assert stored_format(files_of(workspace)) == 3
    assert migrate(files_of(workspace), [ONE_TO_TWO, TWO_TO_THREE], target=3) == ()


def test_migration_is_deterministic(workspace: Workspace, atlas: Workspace) -> None:
    for space in (workspace, atlas):
        space.write("specs/search.md", spec())
        migrate(files_of(space), [ONE_TO_TWO], target=2)
    assert workspace.read("specs/search.md") == atlas.read("specs/search.md")


def test_failed_migration_leaves_the_record_in_the_last_whole_format(
    workspace: Workspace,
) -> None:
    workspace.write("specs/search.md", spec())
    charter = workspace.read("charter.md")
    with pytest.raises(Refusal, match="Nothing was changed"):
        migrate(files_of(workspace), [ONE_TO_TWO, BROKEN], target=3)
    assert stored_format(files_of(workspace)) == 2
    assert "## Aim" in workspace.read("specs/search.md")
    assert workspace.read("charter.md") == charter


def test_advancing_the_format_number_changes_no_other_setting(workspace: Workspace) -> None:
    before = "# a comment\n" + workspace.read("config.toml")
    after = set_record_format(before, 2)
    assert after == before.replace("record_format = 1", "record_format = 2")


def test_record_from_a_newer_wm_is_refused(workspace: Workspace) -> None:
    workspace.replace("config.toml", "record_format = 1", "record_format = 7")
    with pytest.raises(Refusal, match="newer than this wm writes"):
        migrate(files_of(workspace))


def test_missing_migration_step_is_refused(workspace: Workspace) -> None:
    with pytest.raises(Refusal, match="no migration from record format 2 to 3"):
        migrate(files_of(workspace), [ONE_TO_TWO], target=3)
    assert stored_format(files_of(workspace)) == 1


def test_settings_without_a_format_number_are_refused(workspace: Workspace) -> None:
    workspace.replace("config.toml", "record_format = 1\n", "")
    with pytest.raises(Refusal, match="record_format"):
        migrate(files_of(workspace))

"""Names of record files and archived folders."""

import datetime

import pytest

from waymark.record.names import ArchiveName, is_valid_name, parse_archive_name


@pytest.mark.parametrize("name", ["add-limit", "search", "fix-slow-first-query"])
def test_names_are_kebab_case(name: str) -> None:
    assert is_valid_name(name)


@pytest.mark.parametrize(
    "name", ["Add-limit", "add_limit", "add-limit-2", "v2", "add--limit", "-add", "add-", "", "a b"]
)
def test_names_have_no_digits_capitals_or_other_separators(name: str) -> None:
    assert not is_valid_name(name)


def test_archived_folder_is_named_date_then_name() -> None:
    parsed = parse_archive_name("2026-03-09-add-limit")
    assert parsed == ArchiveName(datetime.date(2026, 3, 9), "add-limit")
    assert parsed is not None
    assert parsed.folder == "2026-03-09-add-limit"


@pytest.mark.parametrize(
    "folder", ["add-limit", "2026-13-40-add-limit", "2026-03-09-Add", "2026-03-09"]
)
def test_archived_folder_with_a_bad_date_or_name_is_not_read(folder: str) -> None:
    assert parse_archive_name(folder) is None


def test_archived_folders_sort_by_date() -> None:
    parsed = [parse_archive_name(f) for f in ("2026-03-09-fix-typo", "2025-12-01-add-limit")]
    in_order = sorted(name for name in parsed if name is not None)
    assert [name.name for name in in_order] == ["add-limit", "fix-typo"]

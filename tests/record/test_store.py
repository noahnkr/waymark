"""Writing the record: all of an operation's files, or none of them."""

import pytest

from tests.support import Workspace, document
from waymark.record.files import RecordFiles
from waymark.record.moves import rewrite_links, tick_roadmap_lines
from waymark.record.store import StoreError, Transaction


def transaction(workspace: Workspace) -> Transaction:
    return Transaction(RecordFiles(workspace.path("")))


def test_transaction_writes_nothing_until_it_is_committed(workspace: Workspace) -> None:
    pending = transaction(workspace)
    pending.write("specs/search.md", "# Search\n")
    assert pending.staged("specs/search.md") == "# Search\n"
    assert not workspace.path("specs/search.md").exists()
    pending.commit()
    assert workspace.read("specs/search.md") == "# Search\n"
    assert pending.paths == ("specs/search.md",)


def test_transaction_writes_text_exactly_as_given(workspace: Workspace) -> None:
    text = "﻿# Café\r\nline\rlast"
    pending = transaction(workspace)
    pending.write("specs/search.md", text)
    pending.commit()
    assert workspace.path("specs/search.md").read_bytes() == text.encode("utf-8")
    assert sorted(path.name for path in workspace.path("specs").iterdir()) == ["search.md"]


def test_transaction_moves_a_folder_after_its_writes(workspace: Workspace) -> None:
    workspace.write("changes/add-limit/proposal.md", "old\n")
    pending = transaction(workspace)
    pending.write("changes/add-limit/proposal.md", "new\n")
    pending.move("changes/add-limit", "changes/archive/2026-02-01-add-limit")
    pending.commit()
    assert not workspace.path("changes/add-limit").exists()
    assert workspace.read("changes/archive/2026-02-01-add-limit/proposal.md") == "new\n"


def test_failed_transaction_restores_every_file_and_removes_new_ones(
    workspace: Workspace,
) -> None:
    workspace.write("changes/add-limit/proposal.md", "old\n")
    workspace.write("changes/archive", "a file in the way\n")
    charter = workspace.read("charter.md")
    pending = transaction(workspace)
    pending.write("charter.md", "changed\n")
    pending.write("specs/search.md", "# Search\n")
    pending.move("changes/add-limit", "changes/archive/2026-02-01-add-limit")
    with pytest.raises(StoreError, match="Nothing was changed"):
        pending.commit()
    assert workspace.read("charter.md") == charter
    assert not workspace.path("specs/search.md").exists()
    assert workspace.read("changes/add-limit/proposal.md") == "old\n"


def test_transaction_refuses_to_move_onto_an_existing_folder(workspace: Workspace) -> None:
    workspace.write("changes/add-limit/proposal.md", "one\n")
    workspace.write("changes/archive/2026-02-01-add-limit/proposal.md", "two\n")
    pending = transaction(workspace)
    pending.move("changes/add-limit", "changes/archive/2026-02-01-add-limit")
    with pytest.raises(StoreError):
        pending.commit()
    assert workspace.read("changes/add-limit/proposal.md") == "one\n"
    assert workspace.read("changes/archive/2026-02-01-add-limit/proposal.md") == "two\n"


SOURCE = "changes/add-limit"
TARGET = "changes/archive/2026-02-01-add-limit"


def test_links_into_a_moved_folder_follow_it() -> None:
    doc = document(
        "See [a](../changes/add-limit/proposal.md#why), [b](../changes/add-limit/) and\n"
        "[c](../changes/add-limiter/proposal.md) but not `[d](../changes/add-limit/x.md)`.\n",
        "explorations/paging.md",
    )
    assert rewrite_links(doc, SOURCE, TARGET) == (
        f"See [a](../{TARGET}/proposal.md#why), [b](../{TARGET}/) and\n"
        "[c](../changes/add-limiter/proposal.md) but not `[d](../changes/add-limit/x.md)`.\n"
    )


def test_links_out_of_a_moved_file_are_aimed_from_its_new_place() -> None:
    doc = document(
        "[spec](../../specs/search.md) [own](specs/search.md) [up](../add-order/tasks.md)\n"
        "[web](https://example.com) [anchor](#why)\n",
        "changes/add-limit/design.md",
    )
    assert rewrite_links(doc, SOURCE, TARGET) == (
        "[spec](../../../specs/search.md) [own](specs/search.md) [up](../../add-order/tasks.md)\n"
        "[web](https://example.com) [anchor](#why)\n"
    )


def test_document_without_affected_links_comes_back_unchanged() -> None:
    text = "﻿No links here.\r\nSee [x](../specs/search.md).\r\n"
    doc = document(text, "explorations/paging.md")
    assert rewrite_links(doc, SOURCE, TARGET) == text


def test_link_rewriting_keeps_line_endings_a_byte_order_mark_and_escapes() -> None:
    text = "﻿[a](../changes/add-limit/my%20notes.md)\r\nrest\r\n"
    doc = document(text, "explorations/paging.md")
    assert rewrite_links(doc, SOURCE, TARGET) == (f"﻿[a](../{TARGET}/my%20notes.md)\r\nrest\r\n")


def test_roadmap_lines_linking_into_a_folder_are_ticked() -> None:
    doc = document(
        "# Roadmap\n\n- [ ] [Limit](../../changes/add-limit/proposal.md)\n"
        "- [ ] [Order](../../changes/add-order/proposal.md)\n- [ ] Later\n",
        "milestones/faster-search/roadmap.md",
    )
    assert tick_roadmap_lines(doc, SOURCE) == (
        "# Roadmap\n\n- [x] [Limit](../../changes/add-limit/proposal.md)\n"
        "- [ ] [Order](../../changes/add-order/proposal.md)\n- [ ] Later\n"
    )

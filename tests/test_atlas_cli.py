"""The multi-repo commands through the command line."""

import io
import json
from pathlib import Path

import pytest

from tests.conftest import git_init
from tests.support import ATLAS_CONFIG, CONFIG, Workspace, spec
from tests.views.validator import errors
from waymark.cli import EXIT_OK, EXIT_REFUSED, main
from waymark.views.schemas import SCHEMAS


def run(capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, str, str]:
    code = main(list(arguments))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def shop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Workspace:
    """A project that references the atlas "billing", which sits beside it."""
    billing = Workspace(tmp_path / "billing", CONFIG + '\n[atlas]\nname = "billing"\n')
    billing.write("specs/invoices.md", spec(title="Invoices", purpose="How invoices work."))
    shop = Workspace(tmp_path / "shop", CONFIG + '\n[references.billing]\npath = "../billing"\n')
    git_init(shop.root)
    monkeypatch.chdir(shop.root)
    return shop


def test_ls_and_show_read_a_referenced_atlas_with_from(
    shop: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run(capsys, "ls", "specs", "--from", "billing", "--json")
    assert code == EXIT_OK
    listed = json.loads(out)
    assert errors(listed, SCHEMAS["ls"]) == []
    assert (listed["from"], [e["name"] for e in listed["entries"]]) == ("billing", ["invoices"])
    assert 'wm: note: Found the atlas "billing" through its path hint' in err
    code, out, _ = run(capsys, "show", "invoices", "--from", "billing")
    assert code == EXIT_OK
    assert "Spec: invoices (from the atlas billing, read only)" in out


def test_from_reads_specs_only_and_only_from_referenced_atlases(
    shop: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(capsys, "ls", "changes", "--from", "billing")[0] == EXIT_REFUSED
    code, _, err = run(capsys, "show", "orders", "--from", "billing")
    assert (code, 'has no spec "orders"' in err) == (EXIT_REFUSED, True)
    code, _, err = run(capsys, "ls", "specs", "--from", "auth")
    assert (code, 'references no atlas "auth"' in err) == (EXIT_REFUSED, True)


def test_doctor_prints_a_versioned_payload_without_folders(
    shop: Workspace, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, out, _ = run(capsys, "doctor", "--json")
    payload = json.loads(out)
    assert errors(payload, SCHEMAS["doctor"]) == []
    assert json.dumps(str(tmp_path))[1:-1] not in out
    assert code == (EXIT_OK if payload["ok"] else EXIT_REFUSED)


def test_atlas_doctor_outside_an_atlas_fails(
    shop: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run(capsys, "atlas", "doctor")
    assert code == EXIT_REFUSED
    assert "not an atlas" in out


def test_register_needs_both_a_repo_and_a_folder_or_neither(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    monkeypatch.chdir(atlas.root)
    code, _, err = run(capsys, "atlas", "register", "api")
    assert (code, "or neither" in err) == (EXIT_REFUSED, True)


def test_hook_replies_carry_no_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    atlas = Workspace(tmp_path / "atlas", ATLAS_CONFIG)
    git_init(atlas.root)
    git_init(tmp_path / "suite-api")
    monkeypatch.chdir(atlas.root)
    payload = {
        "cwd": str(atlas.root),
        "tool_name": "Write",
        "agent_type": "wm-implementer",
        "tool_input": {"file_path": str(tmp_path / "suite-api" / "a.py"), "content": "x"},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code, _, err = run(capsys, "hook", "claude-code", "PreToolUse")
    assert code == EXIT_OK
    assert "note:" not in err

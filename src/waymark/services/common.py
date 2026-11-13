"""What every service shares: refusals, results, and opening the record."""

from dataclasses import dataclass
from pathlib import Path

from waymark import __version__
from waymark.record.changes import Change
from waymark.record.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.project import RECORD_DIR, ProjectNotFoundError, find_project
from waymark.record.record import Record, load_record
from waymark.record.state import ChangeState, change_state, overlaps
from waymark.record.store import StoreError, Transaction
from waymark.record.tasks import Item


class Refusal(Exception):  # noqa: N818 - a refusal is an answer, not a fault
    """A command was refused. The message says what is wrong and what to do next."""


@dataclass(frozen=True)
class Done:
    """What a command did, in a sentence, and the record files it wrote."""

    message: str
    paths: tuple[str, ...] = ()


def install_hint(version: str) -> str:
    """The commands that install one exact version of wm."""
    return (
        f"pipx install --force waymark-cli=={version}"
        f"   (or: uv tool install --force waymark-cli=={version})"
    )


def require_pinned(record: Record) -> None:
    """Refuse to write unless the settings are readable and this wm is the pinned version."""
    config = record.config
    if config is None:
        problems = [p for p in record.problems if p.path == CONFIG_FILE]
        detail = problems[0].message if problems else "It could not be read."
        raise Refusal(f"{RECORD_DIR}/{CONFIG_FILE} has problems. {detail}")
    if config.wm_version != __version__:
        raise Refusal(
            f"This project is pinned to wm {config.wm_version}, and this is wm {__version__}. "
            "Reading works with any version, but only the pinned one may write the record. "
            f"Install it with: {install_hint(config.wm_version)}"
        )


def require_writable(record: Record) -> None:
    """Refuse to write unless this wm is the pinned one and the record is in its format."""
    require_pinned(record)
    config = record.config
    assert config is not None
    if config.record_format != RECORD_FORMAT:
        raise Refusal(
            f"The record is in format {config.record_format}, and this wm writes format "
            f'{RECORD_FORMAT}. Run "wm update" to migrate the record.'
        )


def open_record(start: Path, *, writing: bool = False) -> Record:
    """Find and read the record around a folder; with ``writing``, check it may be written."""
    try:
        project = find_project(start)
    except ProjectNotFoundError as error:
        raise Refusal(str(error)) from error
    record = load_record(project)
    if writing:
        require_writable(record)
    return record


def find_change(record: Record, name: str) -> Change:
    """An active change by name."""
    change = record.changes.get(name)
    if change is None:
        active = ", ".join(sorted(record.changes)) or "none"
        raise Refusal(f'There is no active change "{name}". Active changes: {active}.')
    return change


def find_item(change: Change, number: str) -> Item:
    """One of a change's task items by number."""
    item = change.tasks.item(number) if change.tasks else None
    if item is None:
        numbers = ", ".join(i.number for i in change.tasks.items) if change.tasks else ""
        raise Refusal(
            f'The change "{change.name}" has no item {number}. Its items: {numbers or "none"}.'
        )
    return item


def state_of(record: Record, change: Change) -> ChangeState:
    """A change's derived state."""
    return change_state(record, change, overlaps(record))


def commit(transaction: Transaction) -> tuple[str, ...]:
    """Apply a transaction; a failed write becomes a refusal, with the record untouched."""
    try:
        transaction.commit()
    except StoreError as error:
        raise Refusal(str(error)) from error
    return transaction.paths


def one_line(text: str, what: str) -> str:
    """Text for a single evidence line: whitespace collapsed, and not empty."""
    collapsed = " ".join(text.split())
    if not collapsed:
        raise Refusal(f"Give {what}; it is written into the record.")
    return collapsed

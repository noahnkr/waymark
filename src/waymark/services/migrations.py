"""Migrations: moving a record from one format to the next.

Each migration upgrades the record by exactly one format number. It is
deterministic, and it is applied together with the new format number or not at
all. Migrations run only when asked for; nothing here runs on its own.
"""

import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from waymark.record.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.edits import set_record_format
from waymark.record.files import RecordFiles
from waymark.record.store import Transaction
from waymark.services.common import Refusal, commit


@dataclass(frozen=True)
class Migration:
    """One step: from format ``source`` to ``source + 1``.

    ``apply`` reads the record through the files and stages its writes in the
    transaction; it never writes on its own.
    """

    source: int
    summary: str
    apply: Callable[[RecordFiles, Transaction], None]


MIGRATIONS: tuple[Migration, ...] = ()
"""Every migration this version knows. Format 1 is the first, so there are none yet."""


def stored_format(files: RecordFiles) -> int:
    """The format number in the settings, read without judging the other settings."""
    text = files.read(CONFIG_FILE, [])
    try:
        value = tomllib.loads(text or "").get("record_format")
    except tomllib.TOMLDecodeError:
        value = None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise Refusal(
            f'{CONFIG_FILE} has no usable "record_format" number, so wm can\'t tell which '
            "format the record is in. Restore the line; it is written by wm."
        )
    return value


def pending(
    current: int, migrations: Sequence[Migration] = MIGRATIONS, target: int = RECORD_FORMAT
) -> tuple[Migration, ...]:
    """The migrations that take a record from its format to the target, in order."""
    if current > target:
        raise Refusal(
            f"The record is in format {current}, which is newer than this wm writes "
            f"(format {target}). Install the wm version the project is pinned to."
        )
    by_source = {migration.source: migration for migration in migrations}
    chain: list[Migration] = []
    for number in range(current, target):
        if number not in by_source:
            raise Refusal(
                f"There is no migration from record format {number} to {number + 1}. "
                "This is a fault in wm; please report it."
            )
        chain.append(by_source[number])
    return tuple(chain)


def migrate(
    files: RecordFiles,
    migrations: Sequence[Migration] = MIGRATIONS,
    target: int = RECORD_FORMAT,
) -> tuple[str, ...]:
    """Run every pending migration; returns what each one did.

    Each step and its new format number are written together, so a failure
    leaves the record in the last format that fully applied.
    """
    done: list[str] = []
    for migration in pending(stored_format(files), migrations, target):
        transaction = Transaction(files)
        migration.apply(files, transaction)
        config = transaction.staged(CONFIG_FILE) or files.read(CONFIG_FILE, []) or ""
        transaction.write(CONFIG_FILE, set_record_format(config, migration.source + 1))
        commit(transaction)
        done.append(f"format {migration.source} to {migration.source + 1}: {migration.summary}")
    return tuple(done)

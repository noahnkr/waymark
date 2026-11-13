"""The CI workflow: GitHub Actions installs the pinned wm and runs wm check.

It is added only when asked for, with ``wm ci``; ``wm update`` keeps it
current once it exists. In an atlas it belongs in the atlas: code repos'
CI runs nothing from wm.
"""

from pathlib import Path

from waymark.record import templates
from waymark.record.files import RecordFiles
from waymark.record.store import Transaction
from waymark.services.common import Done, commit, open_record, require_pinned

WORKFLOW = ".github/workflows/waymark.yml"


def stage_workflow(transaction: Transaction, files: RecordFiles, *, only_if_present: bool) -> str:
    """Stage the workflow; says whether it was created, updated, unchanged or left out."""
    current = files.read(WORKFLOW, []) if files.is_file(WORKFLOW) else None
    if current is None and only_if_present:
        return "absent"
    text = templates.render(templates.CI_WORKFLOW)
    if current == text:
        return "unchanged"
    transaction.write(WORKFLOW, text)
    return "created" if current is None else "updated"


def add_workflow(start: Path) -> Done:
    """Add, or bring up to date, the workflow that runs wm check in CI."""
    record = open_record(start)
    require_pinned(record)
    files = RecordFiles(record.project.root)
    transaction = Transaction(files)
    status = stage_workflow(transaction, files, only_if_present=False)
    commit(transaction)
    if status == "unchanged":
        return Done(f"{WORKFLOW} is already current.")
    return Done(
        f"{status}: {WORKFLOW}\nOn GitHub, it installs the wm version this project pins and runs "
        '"wm check" on every push and pull request. Review it and commit it.',
        transaction.paths,
    )

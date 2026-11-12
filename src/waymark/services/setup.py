"""Setting up a project, and creating changes, milestones and explorations from templates."""

import re
from pathlib import Path

from waymark import __version__
from waymark.record import git, templates
from waymark.record.changes import PROPOSAL_FILE
from waymark.record.charter import CHARTER_FILE
from waymark.record.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.files import RecordFiles
from waymark.record.milestones import GOAL_FILE, ROADMAP_FILE
from waymark.record.names import NAME_RULE, is_valid_name
from waymark.record.project import RECORD_DIR
from waymark.record.proposal import OWNER, PATH, SHORT
from waymark.record.record import CHANGES, EXPLORATIONS, MILESTONES
from waymark.record.store import Transaction
from waymark.services.common import Done, Refusal, commit, open_record

_ATLAS_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def init_project(start: Path, atlas: str | None = None) -> Done:
    """Create the record at the top of the git repository around a folder."""
    root = git.repository_root(start)
    if root is None:
        raise Refusal(
            'wm needs a git repository, and this folder is not in one. Run "git init" first.'
        )
    files = RecordFiles(root / RECORD_DIR)
    if files.is_file(CONFIG_FILE):
        raise Refusal(
            f"This repository already has a record ({RECORD_DIR}/{CONFIG_FILE}). "
            'Run "wm check" to see how it stands.'
        )
    if atlas is not None and not _ATLAS_NAME.fullmatch(atlas):
        raise Refusal(
            f'"{atlas}" can\'t be an atlas name. Use letters, digits, dots, hyphens or '
            "underscores, starting with a letter or digit."
        )
    config = templates.render(
        templates.CONFIG, wm_version=__version__, record_format=str(RECORD_FORMAT)
    )
    if atlas is not None:
        config += templates.render(templates.ATLAS_CONFIG, atlas_name=atlas)
    transaction = Transaction(files)
    transaction.write(CONFIG_FILE, config)
    transaction.write(CHARTER_FILE, templates.render(templates.CHARTER, title=root.name))
    paths = commit(transaction)
    kind = f'the atlas "{atlas}"' if atlas is not None else "a project"
    return Done(
        f"Initialized {kind} in {RECORD_DIR}/. Next: run the kickoff skill in your agent tool "
        "to draft the charter.",
        paths,
    )


def _require_new_name(name: str, kind: str, taken: bool) -> None:
    article = "an" if kind[0] in "aeiou" else "a"
    if not is_valid_name(name):
        raise Refusal(f'"{name}" can\'t be {article} {kind} name. Use {NAME_RULE}.')
    if taken:
        raise Refusal(f'There already is {article} {kind} named "{name}". Pick another name.')


def create_change(start: Path, name: str, *, short: bool = False, owner: str | None = None) -> Done:
    """Create a change folder with a proposal skeleton."""
    record = open_record(start, writing=True)
    folder = f"{CHANGES}/{name}"
    _require_new_name(name, "change", bool(record.files.entries(folder)))
    who = owner or git.user_name(record.project.root)
    if not who:
        raise Refusal(
            "Every change has one owner. Pass --owner <name>, or set your name in git: "
            'git config user.name "<name>".'
        )
    facts = f"{OWNER}: {who}\n" + (f"{PATH}: {SHORT}\n" if short else "")
    text = templates.render(templates.PROPOSAL, title=templates.title_from_name(name), facts=facts)
    transaction = Transaction(record.files)
    transaction.write(f"{folder}/{PROPOSAL_FILE}", text)
    path = "on the short path " if short else ""
    return Done(f'Created the change "{name}" {path}with a proposal to draft.', commit(transaction))


def create_milestone(start: Path, name: str) -> Done:
    """Create a milestone folder with goal and roadmap skeletons."""
    record = open_record(start, writing=True)
    folder = f"{MILESTONES}/{name}"
    _require_new_name(name, "milestone", bool(record.files.entries(folder)))
    title = templates.title_from_name(name)
    transaction = Transaction(record.files)
    transaction.write(f"{folder}/{GOAL_FILE}", templates.render(templates.GOAL, title=title))
    transaction.write(f"{folder}/{ROADMAP_FILE}", templates.render(templates.ROADMAP, title=title))
    return Done(f'Created the milestone "{name}" with a goal to draft.', commit(transaction))


def create_exploration(start: Path, name: str) -> Done:
    """Create an exploration skeleton."""
    record = open_record(start, writing=True)
    path = f"{EXPLORATIONS}/{name}.md"
    _require_new_name(name, "exploration", record.files.is_file(path))
    transaction = Transaction(record.files)
    transaction.write(
        path, templates.render(templates.EXPLORATION, title=templates.title_from_name(name))
    )
    return Done(f'Created the exploration "{name}".', commit(transaction))

"""Setting up a project, and creating changes, milestones and explorations from templates."""

import re
from pathlib import Path

from waymark import __version__, adapters
from waymark.record import git, templates
from waymark.record.changes import PROPOSAL_FILE
from waymark.record.charter import CHARTER_FILE
from waymark.record.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.files import RecordFiles
from waymark.record.milestones import MILESTONE_FILE, link_change
from waymark.record.names import NAME_RULE, is_valid_name
from waymark.record.pointer import POINTER_FILE, is_pointer, parse_pointer
from waymark.record.project import RECORD_DIR
from waymark.record.proposal import MILESTONE, OWNER, PATH, SHORT
from waymark.record.record import CHANGES, EXPLORATIONS, MILESTONES
from waymark.record.store import Transaction
from waymark.services import integration
from waymark.services.atlas import register_new_atlas
from waymark.services.common import Done, Refusal, commit, open_record

_ATLAS_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def init_project(
    start: Path, atlas: str | None = None, tools: tuple[str, ...] | None = None
) -> Done:
    """Create the record at the top of the git repository around a folder.

    Also installs the skills, agent definitions and hooks for the project's
    agent tools: every tool wm knows, unless ``tools`` names them, and adds the
    ``.gitignore`` block that keeps them out of git. In a repository that
    already has a record, as in a fresh clone, it sets up this machine instead
    and leaves the record alone.
    """
    root = git.repository_root(start)
    if root is None:
        raise Refusal(
            'wm needs a git repository, and this folder is not in one. Run "git init" first.'
        )
    files = RecordFiles(root)
    _refuse_in_a_code_repo(files)
    if files.is_file(f"{RECORD_DIR}/{CONFIG_FILE}"):
        return _set_up_clone(root, atlas, tools)
    if atlas is not None and not _ATLAS_NAME.fullmatch(atlas):
        raise Refusal(
            f'"{atlas}" can\'t be an atlas name. Use letters, digits, dots, hyphens or '
            "underscores, starting with a letter or digit."
        )
    chosen = adapters.names() if tools is None else tools
    integration.require_tools(chosen)
    config = templates.render(
        templates.CONFIG,
        wm_version=__version__,
        record_format=str(RECORD_FORMAT),
        agent_tools=", ".join(f'"{tool}"' for tool in chosen),
    )
    if atlas is not None:
        config += templates.render(templates.ATLAS_CONFIG, atlas_name=atlas)
    transaction = Transaction(files)
    transaction.write(f"{RECORD_DIR}/{CONFIG_FILE}", config)
    transaction.write(
        f"{RECORD_DIR}/{CHARTER_FILE}", templates.render(templates.CHARTER, title=root.name)
    )
    integration.stage_folder_keeps(transaction, files)
    integration.stage(transaction, files, chosen)
    integration.stage_ignore(transaction, files, integration.ignore_patterns(chosen))
    paths = commit(transaction)
    kind = f'the atlas "{atlas}"' if atlas is not None else "a project"
    titles = ", ".join(adapters.get(tool).title for tool in chosen) or "no agent tool"
    registered = f" {register_new_atlas(root, atlas)}" if atlas is not None else ""
    return Done(
        f"Initialized {kind} in {RECORD_DIR}/, with skills, agents and hooks for {titles}."
        f"{registered}\n"
        'To run "wm check" in GitHub Actions too, run "wm ci".\n'
        "Next: run the wm-kickoff skill in your agent tool to draft the charter.",
        paths,
    )


def _refuse_in_a_code_repo(files: RecordFiles) -> None:
    """Refuse ``wm init`` in a code repo that points at an atlas, before anything is written.

    The pointer is a pointer-only ``waymark/config.toml``. A repository with a
    record is left to the caller.
    """
    if not files.is_file(POINTER_FILE):
        return
    text = files.read(POINTER_FILE, [])
    if text is None or not is_pointer(text):
        return
    pointer, _ = parse_pointer(text)
    atlas = f'the atlas "{pointer.atlas}"' if pointer is not None else "an atlas"
    raise Refusal(
        f"This repository is a code repo that points at {atlas} ({POINTER_FILE}), and its record "
        'lives in the atlas. Nothing was written. Run "wm init" in the atlas instead.'
    )


def _set_up_clone(root: Path, atlas: str | None, tools: tuple[str, ...] | None) -> Done:
    """Set up this machine in a repository that already has a record, leaving the record alone.

    Needs the pinned wm and a record in this wm's format; anything else is
    refused before a file is written.
    """
    if atlas is not None or tools is not None:
        raise Refusal(
            f"This repository already has a record ({RECORD_DIR}/{CONFIG_FILE}), so wm init "
            "sets up this machine from its settings, and --atlas and --tool don't apply. "
            f'Run "wm init" without them; to change the agent tools, edit "agent_tools" in '
            f'{RECORD_DIR}/{CONFIG_FILE}, then run "wm update".'
        )
    record = open_record(root, writing=True)
    machine = integration.setup_machine(record)
    changed = [change for change in machine.changes if change.status != "unchanged"]
    lines = [f"{change.status}: {change.path}" for change in changed]
    if changed:
        assert record.config is not None
        tools_set = record.config.agent_tools
        titles = ", ".join(adapters.get(tool).title for tool in tools_set) or "no agent tool"
        lines.append(
            f"This machine is set up, with skills, agents and hooks for {titles}. "
            f"The record in {RECORD_DIR}/ was not changed."
        )
    else:
        lines.append("This machine is already set up. Nothing changed.")
    return Done("\n".join(lines), machine.paths)


def _require_new_name(name: str, kind: str, taken: bool) -> None:
    article = "an" if kind[0] in "aeiou" else "a"
    if not is_valid_name(name):
        raise Refusal(f'"{name}" can\'t be {article} {kind} name. Use {NAME_RULE}.')
    if taken:
        raise Refusal(f'There already is {article} {kind} named "{name}". Pick another name.')


def create_change(
    start: Path,
    name: str,
    *,
    short: bool = False,
    owner: str | None = None,
    milestone: str | None = None,
) -> Done:
    """Create a change folder with a proposal skeleton, linked from its milestone if it has one."""
    record = open_record(start, writing=True)
    folder = f"{CHANGES}/{name}"
    _require_new_name(name, "change", bool(record.files.entries(folder)))
    member = record.milestones.get(milestone) if milestone is not None else None
    if milestone is not None and (member is None or member.roadmap is None):
        known = ", ".join(sorted(record.milestones)) or "none"
        raise Refusal(
            f'"{milestone}" is not an active milestone (the active ones: {known}). Name one of '
            f'them, or create it first with "wm new milestone {milestone}".'
        )
    who = owner or git.user_name(record.project.root)
    if not who:
        raise Refusal(
            "Every change has one owner. Pass --owner <name>, or set your name in git: "
            'git config user.name "<name>".'
        )
    facts = (
        f"- {OWNER}: {who}\n"
        + (f"- {MILESTONE}: {milestone}\n" if milestone else "")
        + (f"- {PATH}: {SHORT}\n" if short else "")
    )
    text = templates.render(templates.PROPOSAL, title=templates.title_from_name(name), facts=facts)
    transaction = Transaction(record.files)
    transaction.write(f"{folder}/{PROPOSAL_FILE}", text)
    path = "on the short path " if short else ""
    message = f'Created the change "{name}" {path}with a proposal to draft.'
    if member is not None and member.roadmap is not None:
        doc = member.roadmap.doc
        target = f"../../{CHANGES}/{name}/{PROPOSAL_FILE}"
        transaction.write(doc.path, link_change(doc, name, target))
        message += f' It is linked from the roadmap of "{milestone}".'
    return Done(message, commit(transaction))


def create_milestone(start: Path, name: str) -> Done:
    """Create a milestone folder with a milestone.md skeleton: its goal and roadmap."""
    record = open_record(start, writing=True)
    folder = f"{MILESTONES}/{name}"
    _require_new_name(name, "milestone", bool(record.files.entries(folder)))
    title = templates.title_from_name(name)
    transaction = Transaction(record.files)
    transaction.write(
        f"{folder}/{MILESTONE_FILE}", templates.render(templates.MILESTONE, title=title)
    )
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

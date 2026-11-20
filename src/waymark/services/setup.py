"""Setting up a project, and creating changes, milestones and explorations from templates."""

import datetime
import re
from pathlib import Path

from waymark import __version__, adapters
from waymark.record.artifacts.changes import PROPOSAL_FILE
from waymark.record.artifacts.charter import CHARTER_FILE
from waymark.record.artifacts.config import CONFIG_FILE, RECORD_FORMAT
from waymark.record.artifacts.explorations import Exploration, with_led_to
from waymark.record.artifacts.milestones import MILESTONE_FILE, append_milestone_log, link_change
from waymark.record.artifacts.proposal import AFTER, MILESTONE, OWNER, PATH, REVIEW, SHORT
from waymark.record.artifacts.resources import KINDS as RESOURCE_KINDS
from waymark.record.evidence import records
from waymark.record.evidence.records import RecordKind
from waymark.record.machine import git
from waymark.record.machine.files import RecordFiles
from waymark.record.machine.pointer import POINTER_FILE, is_pointer, parse_pointer
from waymark.record.machine.project import RECORD_DIR
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.text import Document
from waymark.record.names import NAME_RULE, is_valid_name
from waymark.record.record import CHANGES, EXPLORATIONS, MILESTONES, RESOURCES, Record
from waymark.record.terms import ReviewLevel
from waymark.record.writing import templates
from waymark.record.writing.store import Transaction
from waymark.services import ci as workflow
from waymark.services import integration
from waymark.services.atlas import register_new_atlas
from waymark.services.common import Done, Refusal, commit, open_record

_ATLAS_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def has_record(root: Path) -> bool:
    """Whether the repository at ``root`` already has a record, as a fresh clone does."""
    return RecordFiles(root).is_file(f"{RECORD_DIR}/{CONFIG_FILE}")


def atlas_name_problem(name: str) -> str | None:
    """Why ``name`` can't name an atlas, or None when it can."""
    if _ATLAS_NAME.fullmatch(name):
        return None
    return (
        f'"{name}" can\'t be an atlas name. Use letters, digits, dots, hyphens or '
        "underscores, starting with a letter or digit."
    )


def init_project(
    start: Path,
    atlas: str | None = None,
    tools: tuple[str, ...] | None = None,
    *,
    ci: bool = False,
) -> Done:
    """Create the record at the top of the git repository around a folder.

    Also installs the skills, agent definitions and hooks for the project's
    agent tools: every tool wm knows, unless ``tools`` names them, and adds the
    ``.gitignore`` block that keeps them out of git. With ``ci`` it also adds the
    CI workflow, in the same transaction. In a repository that
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
    problem = atlas_name_problem(atlas) if atlas is not None else None
    if problem is not None:
        raise Refusal(problem)
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
    if ci:
        workflow.stage_workflow(transaction, files, only_if_present=False)
    paths = commit(transaction)
    kind = f'the atlas "{atlas}"' if atlas is not None else "a project"
    titles = ", ".join(adapters.get(tool).title for tool in chosen) or "no agent tool"
    registered = f" {register_new_atlas(root, atlas)}" if atlas is not None else ""
    if ci:
        ci_line = f'Added {workflow.WORKFLOW}, which runs "wm check" in GitHub Actions.\n'
    else:
        ci_line = 'To run "wm check" in GitHub Actions too, run "wm ci".\n'
    return Done(
        f"Initialized {kind} in {RECORD_DIR}/, with skills, agents and hooks for {titles}."
        f"{registered}\n"
        f"{ci_line}"
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


def create_change(  # noqa: PLR0913 - the change's facts, and the day for its milestone's log
    start: Path,
    name: str,
    *,
    short: bool = False,
    owner: str | None = None,
    milestone: str | None = None,
    after: str | None = None,
    today: datetime.date | None = None,
    source: str | None = None,
) -> Done:
    """Create a change folder with a proposal skeleton, linked from its milestone if it has one.

    ``source`` names the exploration the change comes from; its status line then
    leads to the change.
    """
    record = open_record(start, writing=True)
    folder = f"{CHANGES}/{name}"
    _require_new_name(name, "change", bool(record.files.entries(folder)))
    exploration = _source_exploration(record, source)
    if after is not None and not is_valid_name(after):
        raise Refusal(f'"{after}" is not a valid change name: {NAME_RULE}.')
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
    facts = "".join(
        f"{label_line(key, value)}\n"
        for key, value in ((OWNER, who), (MILESTONE, milestone), (AFTER, after))
        if value
    ) + (f"{label_line(PATH, SHORT)}\n" if short else "")
    level = record.default_review
    if short and level is ReviewLevel.INDEPENDENT:
        level = ReviewLevel.SELF
    facts += f"{label_line(REVIEW, level.value)}\n"
    text = templates.render(templates.PROPOSAL, title=templates.title_from_name(name), facts=facts)
    transaction = Transaction(record.files)
    transaction.write(f"{folder}/{PROPOSAL_FILE}", text)
    path = "on the short path " if short else ""
    message = f'Created the change "{name}" {path}with a proposal to draft.'
    if member is not None and member.roadmap is not None:
        doc = member.roadmap.doc
        target = f"../../{CHANGES}/{name}/{PROPOSAL_FILE}"
        linked = Document.parse(doc.path, link_change(doc, name, target))
        entry = records.Record(
            RecordKind.PROPOSED,
            today or datetime.date.today(),
            who=records.who_for(record.project.root, RecordKind.PROPOSED, None),
            change=name,
        )
        transaction.write(doc.path, append_milestone_log(linked, records.render(entry)))
        message += f' It is linked from the roadmap of "{milestone}".'
    if exploration is not None:
        target = f"../{CHANGES}/{name}/{PROPOSAL_FILE}"
        transaction.write(exploration.doc.path, with_led_to(exploration, name, target))
        message += f' The exploration "{exploration.name}" now leads to it.'
    return Done(message, commit(transaction))


def _source_exploration(record: Record, source: str | None) -> Exploration | None:
    """The active exploration a new change or milestone comes from, or None for none."""
    if source is None:
        return None
    exploration = record.explorations.get(source)
    if exploration is None or exploration.status_index is None:
        known = ", ".join(sorted(record.explorations)) or "none"
        raise Refusal(
            f'"{source}" is not an active exploration with a status line (the active ones: '
            f"{known}). Name one of them with --from, or leave --from out."
        )
    return exploration


def create_milestone(start: Path, name: str, source: str | None = None) -> Done:
    """Create a milestone folder with a milestone.md skeleton: its goal and roadmap.

    ``source`` names the exploration the milestone comes from; its status line then
    leads to the milestone.
    """
    record = open_record(start, writing=True)
    folder = f"{MILESTONES}/{name}"
    _require_new_name(name, "milestone", bool(record.files.entries(folder)))
    exploration = _source_exploration(record, source)
    title = templates.title_from_name(name)
    transaction = Transaction(record.files)
    transaction.write(
        f"{folder}/{MILESTONE_FILE}", templates.render(templates.MILESTONE, title=title)
    )
    message = f'Created the milestone "{name}" with a goal to draft.'
    if exploration is not None:
        target = f"../{MILESTONES}/{name}/{MILESTONE_FILE}"
        transaction.write(exploration.doc.path, with_led_to(exploration, name, target))
        message += f' The exploration "{exploration.name}" now leads to it.'
    return Done(message, commit(transaction))


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


def create_resource(
    start: Path, name: str, kind: str | None, today: datetime.date | None = None
) -> Done:
    """Create a resource from the template: its kind as given, serving no spec, active, and
    verified today."""
    record = open_record(start, writing=True)
    path = f"{RESOURCES}/{name}.md"
    _require_new_name(name, "resource", record.files.is_file(path))
    kinds = ", ".join(RESOURCE_KINDS)
    if kind is None:
        raise Refusal(
            f'Name the resource\'s kind: "wm new resource {name} <kind>", one of {kinds}.'
        )
    if kind not in RESOURCE_KINDS:
        raise Refusal(f'"{kind}" is not a kind of resource. The kinds are {kinds}.')
    text = templates.render(
        templates.RESOURCE,
        title=templates.title_from_name(name),
        kind=kind,
        date=(today or datetime.date.today()).isoformat(),
    )
    transaction = Transaction(record.files)
    transaction.write(path, text)
    return Done(f'Created the resource "{name}".', commit(transaction))

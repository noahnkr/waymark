"""The decisions: is this delegation, edit or command allowed, and what does a stop record?

These are guard rails against mistakes, drift and shortcuts. They are not a
security boundary and don't claim to stop deliberate circumvention.
"""

import datetime
import re
from pathlib import Path

from waymark import assets
from waymark.hooks import commands
from waymark.hooks.events import ALLOW, Decision, Event, EventKind, Role
from waymark.record.artifacts.config import CONFIG_FILE, parse_config
from waymark.record.evidence import agents
from waymark.record.evidence.commits import commit_problem
from waymark.record.evidence.evidence import (
    evidence_changes,
    is_active_exploration,
    is_active_milestone,
)
from waymark.record.evidence.records import IMPLEMENTER, REVIEWER, parse_finding_argument
from waymark.record.machine.atlas import contains
from waymark.record.machine.files import RecordFiles
from waymark.record.machine.project import RECORD_DIR, Project, ProjectNotFoundError, find_project
from waymark.record.record import RESOURCES, SPECS, Record, load_record
from waymark.record.state import AcceptanceState, StepKind, derive_state
from waymark.record.terms import Layout, Verdict
from waymark.services import lifecycle
from waymark.services.common import Done, Refusal, find_change, find_item, repo_locations
from waymark.services.context import (
    FINDING_LINE,
    IMPLEMENT,
    RESULT_LINE,
    REVIEW,
    VERDICT_LINE,
    delegation_problems,
)
from waymark.views import payloads, render
from waymark.views.style import Style

_ADDRESS = re.compile(r"(\S+)\s+(\d+\.\d+)")
_CHANGE_ADDRESS = re.compile(r"[a-z0-9][a-z0-9-]*")
_ITEM_LINE = re.compile(r"^\s*ITEM:\s*(\S+)\s+(\d+\.\d+)\s*$", re.MULTILINE)
_CHANGE_LINE = re.compile(r"^\s*CHANGE:\s*(\S+)\s*$", re.MULTILINE)
_RESULT = re.compile(r"^\s*RESULT:\s*(done|partial|spec-gap|blocked)\b[^\w\n]*(.*)$", re.MULTILINE)
_VERDICT = re.compile(
    r"^\s*VERDICT:\s*(pass|changes|spec-gap)\b:?((?:[\s,]+\d+\.\d+)*)[^\w\n]*(.*)$",
    re.MULTILINE,
)
_FINDING = re.compile(r"^\s*FINDING:\s*(.*?)\s*$", re.MULTILINE)

_AGENT_ROLES = {assets.IMPLEMENTER: IMPLEMENT, assets.REVIEWER: REVIEW}
_HANDBACK_TRIES = 2
"""Refused handbacks before the agent is let go and the planner told to record its result."""
_EVIDENCE_COMMANDS = (
    "wm tick, wm block, wm gap, wm note, wm review, wm verdict, wm reopen or wm resolve; "
    "accepting is for the human, with wm accept"
)
_ROADMAP_COMMANDS = (
    'wm roadmap add <milestone> <change> "<description>", wm roadmap drop <milestone> '
    '<change> --reason "<why>" or wm roadmap move <milestone> <change> --after <change>|--first'
)

_EXPLORATION_COMMANDS = (
    "wm new change <name> --from <exploration>, wm new milestone <name> --from <exploration> "
    'or wm exploration drop <exploration> --reason "<why>"'
)


def _commands_for(relative: str) -> str:
    """The commands that write the evidence in a record file."""
    if is_active_milestone(relative):
        return _ROADMAP_COMMANDS
    if is_active_exploration(relative):
        return _EXPLORATION_COMMANDS
    return _EVIDENCE_COMMANDS


def _refuse(reason: str) -> Decision:
    return Decision(allow=False, reason=reason)


def _relative(project: Project, path: Path) -> str | None:
    """A path inside the record, relative to its root; None for a path outside it."""
    try:
        relative = path.resolve().relative_to(project.record_root.resolve())
    except ValueError:
        return None
    return relative.as_posix()


def _session_start(project: Project) -> Decision:
    record = load_record(project)
    status = render.to_text(payloads.status(record), Style())
    lead = (
        "This project uses Waymark: the written record in the waymark/ folder is the source "
        "of truth, and wm says what comes next. Where things stand:"
    )
    tail = 'Run "wm inbox" for what needs the human, and "wm instructions" for the next step.'
    return Decision(context=f"{lead}\n\n{status}\n\n{tail}")


def _delegate(project: Project, event: Event) -> Decision:
    role = _AGENT_ROLES.get(event.agent)
    if role is None:
        return ALLOW
    if role == REVIEW:
        return _delegate_review(project, event)
    address = _ADDRESS.fullmatch(event.prompt.strip())
    if address is None:
        return _refuse(
            f'Start the {event.agent} agent with exactly "<change> <item>", for example '
            '"add-search-limit 1.2", and nothing else. It builds its own context from the '
            "record; anything it needs that isn't there is a spec gap."
        )
    record = load_record(project)
    try:
        change = find_change(record, address.group(1))
        item = find_item(change, address.group(2))
    except Refusal as refusal:
        return _refuse(str(refusal))
    problems = delegation_problems(record, change, item, role)
    return _refuse(problems[0]) if problems else ALLOW


def _delegate_review(project: Project, event: Event) -> Decision:
    """A reviewer is started with the change's name alone, and only when the change needs it."""
    prompt = event.prompt.strip()
    if _CHANGE_ADDRESS.fullmatch(prompt) is None:
        return _refuse(
            f'Start the {event.agent} agent with exactly "<change>", for example '
            '"add-search-limit", and nothing else. It reviews the whole change from the record.'
        )
    record = load_record(project)
    try:
        change = find_change(record, prompt)
    except Refusal as refusal:
        return _refuse(str(refusal))
    problems = delegation_problems(record, change, None, REVIEW)
    return _refuse(problems[0]) if problems else ALLOW


def _new_text(files: RecordFiles, relative: str, event: Event) -> tuple[str, str | None]:
    """A file's text now, and after the edit; the second is None when it can't be known."""
    before = files.read(relative, []) or "" if files.is_file(relative) else ""
    if event.content is not None:
        return before, event.content
    if not event.replacements:
        return before, None
    after = before
    for replacement in event.replacements:
        if not replacement.old or replacement.old not in after:
            return before, None
        count = -1 if replacement.everywhere else 1
        after = after.replace(replacement.old, replacement.new, count)
    return before, after


def editable_repos(record: Record) -> dict[str, list[str]]:
    """The code repos an implementer may edit now, each with the items that name it.

    The hook can't see which item an implementer was started on, so the record
    answers: in each accepted change, the next item to apply is the one being
    built, and its repo is the one an implementer may edit. The planner may edit
    any code repo.
    """
    repos: dict[str, list[str]] = {}
    for name, state in sorted(derive_state(record).changes.items()):
        step = state.next_step
        if state.acceptance is not AcceptanceState.VALID or step.kind is not StepKind.APPLY:
            continue
        tasks = record.changes[name].tasks
        item = tasks.item(step.item) if tasks and step.item else None
        if item is not None and item.repo:
            repos.setdefault(item.repo, []).append(f"{name} {item.number}")
    return repos


def _places(record: Record, allowed: dict[str, list[str]]) -> str:
    """Each repo that may be edited now, where it is and the items that name it."""
    locations = repo_locations(record)
    places = []
    for repo, items in sorted(allowed.items()):
        location = locations.get(repo)
        folder = location.folder if location else None
        where = str(folder) if folder else "not found on this machine; register it with wm atlas"
        places.append(f'"{repo}" ({where}) for {", ".join(items)}')
    return "; ".join(places)


def _outside_record(project: Project, event: Event) -> Decision:
    """An implementer's edit limit across an atlas's code repos.

    The planner, working from the atlas, may edit any code repo; elsewhere every
    role but the reviewer may edit.
    """
    if event.role is Role.PLANNER:
        return ALLOW
    record = load_record(project)
    if event.path is None or record.layout is not Layout.ATLAS:
        return ALLOW
    inside = next(
        (
            name
            for name, location in repo_locations(record).items()
            if location.folder is not None and contains(location.folder, event.path)
        ),
        None,
    )
    allowed = editable_repos(record)
    if inside is not None and inside in allowed:
        return ALLOW
    if not allowed:
        return _refuse(
            "No accepted change has an item to apply right now, so there is no code repo "
            "an implementer may edit. Check the item with wm show <change>."
        )
    return _refuse(
        "An implementer edits only inside the code repo its item names: "
        f"{_places(record, allowed)}. This file is outside it. If the item needs changes "
        "elsewhere, end with RESULT: spec-gap and say what is missing."
    )


def _edit(project: Project, event: Event) -> Decision:  # noqa: PLR0911 - one return per rule
    if event.role is Role.REVIEWER:
        return _refuse(
            "A reviewer edits nothing: not the code and not the record. Report what you "
            "found in your verdict instead."
        )
    relative = _relative(project, event.path) if event.path else None
    if relative is None:
        return _outside_record(project, event)
    parts = relative.split("/")
    if parts[0] == SPECS:
        return _refuse(
            "Specs are never edited by hand: they change only when a change is archived or "
            "synced. Write a delta in the change's specs folder instead."
        )
    if parts[0] == RESOURCES:
        return ALLOW
    if event.role is Role.IMPLEMENTER:
        return _refuse(
            "An implementer doesn't edit the record. Leave a note on your item with "
            '"wm note <change> <item> "<text>"", or end with RESULT: partial and a note; '
            "if the record needs to change, end with RESULT: spec-gap and say what is missing."
        )
    before, after = _new_text(RecordFiles(project.record_root), relative, event)
    if after is None:
        return ALLOW
    changed = evidence_changes(relative, before, after)
    if changed:
        return _refuse(
            f"This edit {changed[0]}. That is evidence, and only wm writes evidence. "
            f"Leave those lines as they are and use a command instead: "
            f"{_commands_for(relative)}."
        )
    return ALLOW


def _edited(project: Project, event: Event) -> Decision:
    relative = _relative(project, event.path) if event.path else None
    if relative is None:
        return ALLOW
    problems = [problem for problem in load_record(project).problems if problem.path == relative]
    if not problems:
        return ALLOW
    lines = [f"- line {problem.line}: {problem.message}" for problem in problems]
    count = f"{len(problems)} format problem{'s' if len(problems) != 1 else ''}"
    return _refuse(
        f"{RECORD_DIR}/{relative} has {count} that wm can't read past. Fix "
        f"{'them' if len(problems) != 1 else 'it'} in the file:\n" + "\n".join(lines)
    )


def _commit_scopes(project: Project) -> tuple[str, ...] | None:
    """The project's commit scopes, if it lists any; None means any scope is accepted."""
    text = RecordFiles(project.record_root).read(CONFIG_FILE, [])
    config = parse_config(text)[0] if text is not None else None
    return config.commit_scopes if config else None


def _message_text(event: Event, message: commands.CommitMessage) -> str | None:
    """A commit's message: given on the command line, or read from the file -F names."""
    if message.file is None:
        return message.text
    path = Path(message.file)
    if not path.is_absolute():
        path = event.cwd / path
    return RecordFiles(path.parent).read(path.name, [])


def _commit_messages(project: Project, event: Event) -> Decision:
    """Refuse a git commit whose message isn't a conventional commit; unreadable ones pass."""
    found = commands.commit_messages(event.command)
    texts = [_message_text(event, message) for message in found if message is not None]
    readable = [text for text in texts if text is not None]
    if not readable:
        return ALLOW
    scopes = _commit_scopes(project)
    for text in readable:
        problem = commit_problem(text, scopes)
        if problem is not None:
            return _refuse(f"The commit was stopped: {problem}")
    return ALLOW


def _by_implementer(arguments: tuple[str, ...]) -> bool:
    """Whether a command's arguments say ``--by implementer``, in either spelling."""
    pairs = zip(arguments, (*arguments[1:], ""), strict=True)
    return any(
        (flag == "--by" and value == IMPLEMENTER) or flag == f"--by={IMPLEMENTER}"
        for flag, value in pairs
    )


def _command(project: Project, event: Event) -> Decision:  # noqa: PLR0911 - one return per rule
    for call in commands.wm_calls(event.command):
        if call.subcommand == "accept":
            return _refuse(
                "Only the human accepts a change. Summarize it for them and ask them to run "
                f'"{call.text}" themselves.'
            )
        if call.subcommand == "archive" and any(a.startswith("--override") for a in call.arguments):
            return _refuse(
                "Only the human may archive past a missing review. Tell them which review is "
                "missing; they can run the command with --override themselves."
            )
    if event.role is Role.PLANNER:
        return _commit_messages(project, event)
    writing = commands.writing_wm_call(event.command)
    note_by_implementer = (
        writing is not None and writing.subcommand == "note" and event.role is Role.IMPLEMENTER
    )
    if writing is not None and not note_by_implementer:
        return _refuse(
            f'"wm {writing.subcommand}" writes the record, and a delegated agent does not. '
            "wm records your result from your final lines. Reading commands such as "
            '"wm context" and "wm show" are fine.'
        )
    if writing is not None and not _by_implementer(writing.arguments):
        return _refuse(
            f'Your note names who wrote it: add "--by {IMPLEMENTER}" to "wm note", so the '
            "record doesn't credit the human or the planner with it."
        )
    pushing = commands.commits_or_pushes(event.command)
    if pushing is not None:
        return _refuse(
            f'A delegated agent does not run "git {pushing.subcommand}". The planner commits '
            "once the item's review has passed."
        )
    if event.role is Role.REVIEWER:
        change = commands.state_change(event.command)
        if change is not None:
            return _refuse(
                f"A reviewer runs read-only commands, and here {change}. Read the code and "
                "run the tests; report anything that needs changing in your verdict."
            )
    return _commit_messages(project, event)


def _ending(role: Role) -> str:
    if role is Role.REVIEWER:
        return (
            'End your reply with two lines and nothing after them: "CHANGE: <change>", '
            f'then "{VERDICT_LINE}" followed by your reasons. Give each finding before them '
            f'on a line of its own: "{FINDING_LINE}".'
        )
    return (
        'End your reply with two lines and nothing after them: "ITEM: <change> <item>", '
        f'then "{RESULT_LINE}" followed by a short note.'
    )


def _record_verdict(project: Project, message: str, today: datetime.date) -> Done:
    """Write the reviewer's verdict on the change, with the items and findings it names."""
    address = _CHANGE_LINE.findall(message)
    outcome = _VERDICT.findall(message)
    if not address or not outcome:
        raise Refusal(_ending(Role.REVIEWER))
    name = address[-1]
    word, named, note = outcome[-1]
    findings = _FINDING.findall(message)
    unreadable = [text for text in findings if parse_finding_argument(text) is None]
    if unreadable:
        raise Refusal(
            f'"FINDING: {unreadable[0]}" is not a finding wm can read. Write each one as '
            f'"{FINDING_LINE}". {_ending(Role.REVIEWER)}'
        )
    items = re.findall(r"\d+\.\d+", named)
    return lifecycle.verdict(
        project.root,
        name,
        Verdict(word),
        note,
        today,
        items=items,
        findings=findings,
        by=REVIEWER,
    )


def _record(project: Project, role: Role, message: str, today: datetime.date) -> Done:
    """Write what the agent's final lines report; refused when they can't be recorded."""
    if role is Role.REVIEWER:
        return _record_verdict(project, message, today)
    address = _ITEM_LINE.findall(message)
    outcome = _RESULT.findall(message)
    if not address or not outcome:
        raise Refusal(_ending(role))
    (name, number), (word, note) = address[-1], outcome[-1]
    root = project.root
    if word == "done":
        return lifecycle.tick(root, name, number)
    if word == "blocked":
        return lifecycle.block(root, name, number, note, today, by=IMPLEMENTER)
    if word == "spec-gap":
        return lifecycle.report_gap(root, name, number, note, today, by=IMPLEMENTER)
    text = f"partial: {note}" if note else "partial"
    return lifecycle.add_note(root, name, number, text, today, by=IMPLEMENTER)


def _gave_up(role: Role, refusal: Refusal) -> Decision:
    return Decision(
        notice=f"Waymark recorded nothing for the {role.value}: {refusal} "
        "Record its result yourself with the wm commands."
    )


def _handback(project: Project, event: Event, today: datetime.date) -> Decision:
    """An agent hands its report back through its tool: record its ending from the report.

    A report without an ending is refused, so the agent hands back again with
    one; the second refusal lets it through with a notice for the planner.
    """
    if event.role is Role.PLANNER:
        return ALLOW
    try:
        done = _record(project, event.role, event.message, today)
    except Refusal as refusal:
        if agents.count_attempt(project.root, event.agent_id) >= _HANDBACK_TRIES:
            return _gave_up(event.role, refusal)
        return _refuse(f"wm could not record your result. {refusal}")
    agents.mark_recorded(project.root, event.agent_id)
    return Decision(notice=f"Waymark: {done.message}")


def _agent_stop(project: Project, event: Event, today: datetime.date) -> Decision:
    if event.role is Role.PLANNER:
        return ALLOW
    marker = agents.read_marker(project.root, event.agent_id)
    if marker is not None and (marker.recorded or marker.attempts >= _HANDBACK_TRIES):
        agents.remove_marker(project.root, event.agent_id)
        return ALLOW
    try:
        done = _record(project, event.role, event.message, today)
    except Refusal as refusal:
        if event.retried:
            agents.remove_marker(project.root, event.agent_id)
            return _gave_up(event.role, refusal)
        return _refuse(f"wm could not record your result. {refusal}")
    agents.remove_marker(project.root, event.agent_id)
    return Decision(notice=f"Waymark: {done.message}")


def decide(event: Event, today: datetime.date) -> Decision:  # noqa: PLR0911
    """Answer one event. Outside a Waymark project every event is allowed."""
    try:
        project = find_project(event.cwd)
    except ProjectNotFoundError:
        return ALLOW
    if event.kind is EventKind.SESSION_START:
        return _session_start(project)
    if event.kind is EventKind.DELEGATE:
        return _delegate(project, event)
    if event.kind is EventKind.EDIT:
        return _edit(project, event)
    if event.kind is EventKind.EDITED:
        return _edited(project, event)
    if event.kind is EventKind.COMMAND:
        return _command(project, event)
    if event.kind is EventKind.HANDBACK:
        return _handback(project, event, today)
    return _agent_stop(project, event, today)

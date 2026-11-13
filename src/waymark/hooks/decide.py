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
from waymark.record.changes import TASKS_FILE
from waymark.record.evidence import evidence_changes, only_adds_notes
from waymark.record.files import RecordFiles
from waymark.record.project import RECORD_DIR, Project, ProjectNotFoundError, find_project
from waymark.record.record import ARCHIVE, CHANGES, SPECS, load_record
from waymark.record.terms import Verdict
from waymark.services import lifecycle
from waymark.services.common import Done, Refusal, find_change, find_item
from waymark.services.context import (
    IMPLEMENT,
    RESULT_LINE,
    REVIEW,
    VERDICT_LINE,
    delegation_problems,
)
from waymark.views import payloads, render
from waymark.views.style import Style

_ADDRESS = re.compile(r"(\S+)\s+(\d+\.\d+)")
_ITEM_LINE = re.compile(r"^\s*ITEM:\s*(\S+)\s+(\d+\.\d+)\s*$", re.MULTILINE)
_RESULT = re.compile(r"^\s*RESULT:\s*(done|partial|spec-gap|blocked)\b[^\w\n]*(.*)$", re.MULTILINE)
_VERDICT = re.compile(r"^\s*VERDICT:\s*(pass|changes|spec-gap)\b[^\w\n]*(.*)$", re.MULTILINE)

_AGENT_ROLES = {assets.IMPLEMENTER: IMPLEMENT, assets.REVIEWER: REVIEW}
_EVIDENCE_COMMANDS = (
    "wm tick, wm block, wm gap, wm review, wm verdict, wm reopen or wm resolve; "
    "accepting is for the human, with wm accept"
)


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


def _edit(project: Project, event: Event) -> Decision:  # noqa: PLR0911 - one return per rule
    if event.role is Role.REVIEWER:
        return _refuse(
            "A reviewer edits nothing: not the code and not the record. Report what you "
            "found in your verdict instead."
        )
    relative = _relative(project, event.path) if event.path else None
    if relative is None:
        return ALLOW
    parts = relative.split("/")
    if parts[0] == SPECS:
        return _refuse(
            "Specs are never edited by hand: they change only when a change is archived or "
            "synced. Write a delta in the change's specs folder instead."
        )
    before, after = _new_text(RecordFiles(project.record_root), relative, event)
    if event.role is Role.IMPLEMENTER:
        own_tasks = parts[0] == CHANGES and parts[1:2] != [ARCHIVE] and parts[-1] == TASKS_FILE
        if not own_tasks or after is None or not only_adds_notes(before, after):
            return _refuse(
                'An implementer may add "  - Note: <text>" lines under its own item in the '
                f"change's {TASKS_FILE}, and nothing else in the record. If the record needs "
                "to change, end with RESULT: spec-gap and say what is missing."
            )
    if after is None:
        return ALLOW
    changed = evidence_changes(relative, before, after)
    if changed:
        return _refuse(
            f"This edit {changed[0]}. That is evidence, and only wm writes evidence. "
            f"Leave those lines as they are and use a command instead: {_EVIDENCE_COMMANDS}."
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


def _command(event: Event) -> Decision:  # noqa: PLR0911 - one return per rule
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
        return ALLOW
    writing = commands.writing_wm_call(event.command)
    if writing is not None:
        return _refuse(
            f'"wm {writing.subcommand}" writes the record, and a delegated agent does not. '
            "wm records your result from your final lines. Reading commands such as "
            '"wm context" and "wm show" are fine.'
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
    return ALLOW


def _ending(role: Role) -> str:
    line = RESULT_LINE if role is Role.IMPLEMENTER else VERDICT_LINE
    return (
        'End your reply with two lines and nothing after them: "ITEM: <change> <item>", '
        f'then "{line}" followed by a short note.'
    )


def _record(project: Project, role: Role, message: str, today: datetime.date) -> Done:
    """Write what the agent's final lines report; refused when they can't be recorded."""
    address = _ITEM_LINE.findall(message)
    outcome = (_RESULT if role is Role.IMPLEMENTER else _VERDICT).findall(message)
    if not address or not outcome:
        raise Refusal(_ending(role))
    (name, number), (word, note) = address[-1], outcome[-1]
    root = project.root
    if role is Role.REVIEWER:
        return lifecycle.verdict(root, name, number, Verdict(word), note, today)
    if word == "done":
        return lifecycle.tick(root, name, number)
    if word == "blocked":
        return lifecycle.block(root, name, number, note)
    if word == "spec-gap":
        return lifecycle.report_gap(root, name, number, note)
    return lifecycle.add_note(root, name, number, f"partial: {note}" if note else "partial")


def _agent_stop(project: Project, event: Event, today: datetime.date) -> Decision:
    if event.role is Role.PLANNER:
        return ALLOW
    try:
        done = _record(project, event.role, event.message, today)
    except Refusal as refusal:
        if event.retried:
            return Decision(
                notice=f"Waymark recorded nothing for the {event.role.value}: {refusal} "
                "Record its result yourself with the wm commands."
            )
        return _refuse(f"wm could not record your result. {refusal}")
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
        return _command(event)
    return _agent_stop(project, event, today)

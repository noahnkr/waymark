"""The ``wm`` command: parses arguments, calls services, prints what they return.

This layer stays thin. Every decision is made by a service; a refused command
prints why and what to do next, and exits with ``EXIT_REFUSED``.
"""

import argparse
import datetime
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from waymark import __version__, adapters
from waymark.record.machine import git
from waymark.record.terms import Step, Verdict
from waymark.services import atlas as atlas_service
from waymark.services import ci as ci_service
from waymark.services import context as context_service
from waymark.services import doctor as doctor_service
from waymark.services import fix as fix_service
from waymark.services import instructions as instructions_service
from waymark.services import integration, lifecycle, references, roadmap, setup
from waymark.services import pr as pr_service
from waymark.services.common import Done, Refusal, open_record, take_notices
from waymark.views import init_flow, payloads, render, welcome
from waymark.views.payloads import Payload
from waymark.views.style import STRONG, Style
from waymark.views.terminal import RawModeUnavailable, RawTerminal

EXIT_OK = 0
"""The command succeeded."""

EXIT_REFUSED = 1
"""The command was refused, or it found problems."""

EXIT_USAGE = 2
"""The command line was wrong."""

PROG = "wm"

Handler = Callable[[argparse.Namespace], int]


def _report(done: Done) -> int:
    if done.message:
        print(done.message)
    return EXIT_OK


def _here() -> Path:
    return Path.cwd()


def _today() -> datetime.date:
    return datetime.date.today()


def _on_a_terminal() -> bool:
    """Whether both input and output are a terminal, so wm init may ask questions."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _init(args: argparse.Namespace) -> int:
    tools = tuple(args.tool) if args.tool else None
    if args.yes or args.atlas is not None or tools is not None or not _on_a_terminal():
        return _report(setup.init_project(_here(), args.atlas, tools))
    root = git.repository_root(_here())
    if root is None:
        return _report(setup.init_project(_here()))
    style = Style.detect(sys.stdout, os.environ)
    try:
        try:
            with RawTerminal() as terminal:
                answers = _init_answers(root, style, terminal)
        except RawModeUnavailable:
            answers = _init_answers(root, style, None)
    except KeyboardInterrupt:
        # Windows delivers Ctrl+C as an interrupt, not a key; it cancels all the same.
        answers = None
    # Raw mode is over by now, so what follows prints as ordinary lines.
    if answers is None:
        print(welcome.CANCELED)
        return EXIT_REFUSED
    if answers is _CLONE:
        return _report(setup.init_project(root))
    done = setup.init_project(root, answers.atlas, answers.tools, ci=answers.ci)
    print(style.paint("Created:", STRONG))
    for path in done.paths:
        print(f"  {path}")
    return _report(done)


_CLONE = init_flow.Answers(None, (), ci=False)
"""Stands for a clone: a record is already here, so no question is asked."""


def _init_answers(
    root: Path, style: Style, terminal: RawTerminal | None
) -> init_flow.Answers | None:
    """The welcome screen and the questions; None when they are canceled."""
    started = welcome.play(terminal, style) if terminal else welcome.show_still(style)
    if not started:
        return None
    if setup.has_record(root):
        return _CLONE
    tools = [
        init_flow.Tool(name, adapters.get(name).title, adapters.get(name).detect(root))
        for name in adapters.names()
    ]
    asker = init_flow.RawAsker(terminal, style) if terminal else init_flow.LineAsker(style)
    return init_flow.ask_answers(asker, tools, setup.atlas_name_problem)


def _update(_: argparse.Namespace) -> int:
    return _report(integration.update(_here()))


def _atlas_register(args: argparse.Namespace) -> int:
    if (args.repo is None) != (args.folder is None):
        raise Refusal("Give both the code repo's name and its folder, or neither.")
    return _report(atlas_service.register(_here(), args.repo, args.folder))


def _atlas_point(args: argparse.Namespace) -> int:
    return _report(atlas_service.point(_here(), args.atlas, args.path))


def _ci(_: argparse.Namespace) -> int:
    return _report(ci_service.add_workflow(_here()))


def _pr(args: argparse.Namespace) -> int:
    _show_payload(pr_service.describe(open_record(_here()), args.change, args.repo), args)
    return EXIT_OK


def _doctor_report(report: doctor_service.Report, args: argparse.Namespace) -> int:
    _show_payload(payloads.doctor(report), args)
    return EXIT_REFUSED if report.failed else EXIT_OK


def _doctor(args: argparse.Namespace) -> int:
    return _doctor_report(doctor_service.doctor(_here()), args)


def _atlas_doctor(args: argparse.Namespace) -> int:
    return _doctor_report(doctor_service.atlas_doctor(_here()), args)


def _hook(args: argparse.Namespace) -> int:
    """Answer an agent tool's hook. A fault here never blocks the agent: it exits 1."""
    try:
        adapter = adapters.get(args.tool)
    except adapters.UnknownToolError:
        known = ", ".join(adapters.names())
        raise Refusal(
            f'"{args.tool}" is not an agent tool wm knows. Known tools: {known}.'
        ) from None
    raw = getattr(sys.stdin, "buffer", None)
    text = raw.read().decode("utf-8", errors="replace") if raw is not None else sys.stdin.read()
    try:
        payload = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as error:
        raise Refusal(f"The hook's input is not JSON ({error}).") from error
    if not isinstance(payload, dict):
        raise Refusal("The hook's input is not a JSON object.")
    reply = adapter.hook(args.event, payload, _here(), _today())
    if reply.stdout:
        print(reply.stdout)
    if reply.stderr:
        print(reply.stderr, file=sys.stderr)
    return reply.code


def _new(args: argparse.Namespace) -> int:
    if args.kind != "resource" and args.resource_kind is not None:
        raise Refusal(
            f'"{args.resource_kind}" is a resource\'s kind; only "wm new resource" takes one.'
        )
    if args.kind == "change":
        return _report(
            setup.create_change(
                _here(),
                args.name,
                short=args.short,
                owner=args.owner,
                milestone=args.milestone,
                after=args.after,
                today=_today(),
                source=args.source,
            )
        )
    if args.short or args.owner or args.milestone or args.after:
        raise Refusal("--short, --owner, --milestone and --after apply to a change only.")
    if args.kind == "milestone":
        return _report(setup.create_milestone(_here(), args.name, args.source))
    if args.source:
        raise Refusal("--from applies to a change or a milestone only.")
    if args.kind == "resource":
        return _report(setup.create_resource(_here(), args.name, args.resource_kind, _today()))
    return _report(setup.create_exploration(_here(), args.name))


def _accept(args: argparse.Namespace) -> int:
    return _report(lifecycle.accept(_here(), args.change, _today(), by=args.by))


def _tick(args: argparse.Namespace) -> int:
    return _report(lifecycle.tick(_here(), args.change, args.item, _today(), by=args.by))


def _block(args: argparse.Namespace) -> int:
    done = lifecycle.block(_here(), args.change, args.item, args.reason, _today(), by=args.by)
    return _report(done)


def _gap(args: argparse.Namespace) -> int:
    done = lifecycle.report_gap(_here(), args.change, args.item, args.note, _today(), by=args.by)
    return _report(done)


def _note(args: argparse.Namespace) -> int:
    done = lifecycle.add_note(_here(), args.change, args.item, args.text, _today(), by=args.by)
    return _report(done)


def _revise(args: argparse.Namespace) -> int:
    parts = [part.strip() for part in args.parts.split(",") if part.strip()]
    done = lifecycle.revise(_here(), args.change, args.why, _today(), parts=parts, by=args.by)
    return _report(done)


def _review(args: argparse.Namespace) -> int:
    done = lifecycle.self_review(
        _here(),
        args.change,
        args.self_summary,
        _today(),
        findings=args.finding or (),
        by=args.by,
    )
    return _report(done)


def _verdict(args: argparse.Namespace) -> int:
    result = Verdict(args.verdict)
    done = lifecycle.verdict(
        _here(),
        args.change,
        result,
        args.reasons,
        _today(),
        items=args.items or (),
        findings=args.finding or (),
        by=args.by,
    )
    return _report(done)


def _reopen(args: argparse.Namespace) -> int:
    return _report(lifecycle.reopen(_here(), args.change, args.item, _today(), by=args.by))


def _resolve(args: argparse.Namespace) -> int:
    done = lifecycle.resolve(_here(), args.change, args.item, args.decision, _today(), by=args.by)
    return _report(done)


def _sync(args: argparse.Namespace) -> int:
    return _report(lifecycle.sync(_here(), args.change, _today(), by=args.by))


def _archive(args: argparse.Namespace) -> int:
    done = lifecycle.archive(
        _here(),
        args.change,
        _today(),
        built=args.built,
        differs=args.differs,
        override=args.override,
        by=args.by,
    )
    return _report(done)


def _roadmap_add(args: argparse.Namespace) -> int:
    return _report(
        roadmap.add(_here(), args.milestone, args.change, args.description, _today(), by=args.by)
    )


def _roadmap_drop(args: argparse.Namespace) -> int:
    return _report(
        roadmap.drop(_here(), args.milestone, args.change, args.reason, _today(), by=args.by)
    )


def _exploration_drop(args: argparse.Namespace) -> int:
    return _report(lifecycle.drop_exploration(_here(), args.exploration, args.reason, _today()))


def _roadmap_move(args: argparse.Namespace) -> int:
    after = None if args.first else args.after
    return _report(
        roadmap.move(_here(), args.milestone, args.change, _today(), after=after, by=args.by)
    )


def _close(args: argparse.Namespace) -> int:
    return _report(lifecycle.close_milestone(_here(), args.milestone, _today()))


def _show_payload(payload: Payload, args: argparse.Namespace) -> None:
    """Print a view: as JSON when asked, otherwise as text styled for this terminal."""
    if args.json:
        print(render.to_json(payload))
    else:
        print(render.to_text(payload, Style.detect(sys.stdout, os.environ)))


def _status(args: argparse.Namespace) -> int:
    _show_payload(payloads.status(open_record(_here())), args)
    return EXIT_OK


def _inbox(args: argparse.Namespace) -> int:
    _show_payload(payloads.inbox(open_record(_here())), args)
    return EXIT_OK


def _show(args: argparse.Namespace) -> int:
    record = open_record(_here())
    if args.source is None:
        _show_payload(payloads.show(record, args.name, args.kind), args)
        return EXIT_OK
    if args.kind not in (None, "spec"):
        raise Refusal("--from reads another atlas's specs only.")
    other = references.reference_record(record, args.source)
    spec = other.specs.get(args.name)
    if spec is None:
        listed = ", ".join(sorted(other.specs)) or "none"
        raise Refusal(f'The atlas "{args.source}" has no spec "{args.name}" (specs: {listed}).')
    _show_payload(payloads.show_spec(other, spec, args.source), args)
    return EXIT_OK


def _ls(args: argparse.Namespace) -> int:
    kind = args.kind.removesuffix("s")
    record = open_record(_here())
    if args.source is not None:
        if kind != "spec":
            raise Refusal("--from lists another atlas's specs only: wm ls specs --from <atlas>")
        record = references.reference_record(record, args.source)
    payload = payloads.ls(record, kind, archived=args.archived, source=args.source)
    _show_payload(payload, args)
    return EXIT_OK


def _instructions(args: argparse.Namespace) -> int:
    payload = instructions_service.instructions(open_record(_here()), args.step, args.change)
    _show_payload(payload, args)
    return EXIT_OK


def _context(args: argparse.Namespace) -> int:
    payload = context_service.context_pack(open_record(_here()), args.role, args.change, args.item)
    _show_payload(payload, args)
    return EXIT_OK


def _check(args: argparse.Namespace) -> int:
    if args.fix:
        if args.json:
            raise Refusal("--fix reports what it changed as text. Run it without --json.")
        fixed = fix_service.fix_layout(_here())
        for file in fixed:
            print(f"Fixed {file.path}: {', '.join(fix.value for fix in file.fixes)}.")
        if not fixed:
            print("Nothing to fix: the record is in its standard layout.")
    now = datetime.datetime.now(datetime.UTC)
    payload = payloads.check(open_record(_here()), now)
    _show_payload(payload, args)
    return EXIT_REFUSED if payload["errors"] else EXIT_OK


def _usage(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return EXIT_OK


def _view_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
    name: str,
    handler: Handler,
    summary: str,
) -> argparse.ArgumentParser:
    parser = commands.add_parser(name, help=summary, description=summary)
    parser.add_argument(
        "--json", action="store_true", help="print the view as JSON, with its schema version"
    )
    parser.set_defaults(handler=handler)
    return parser


def _item_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
    name: str,
    handler: Handler,
    summary: str,
) -> argparse.ArgumentParser:
    parser = commands.add_parser(name, help=summary, description=summary)
    parser.add_argument("change", help="the change's name")
    parser.add_argument("item", help="the item's number, for example 1.2")
    parser.set_defaults(handler=handler)
    return parser


def _by(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add --by: who the record names as its writer, in place of who its kind names."""
    parser.add_argument(
        "--by",
        metavar="NAME",
        help=(
            "who the record names as its writer (default: your git name for your own acts, "
            '"planner for <your git name>" for what the planner writes)'
        ),
    )
    return parser


def build_parser() -> argparse.ArgumentParser:  # noqa: PLR0915 - one flat list of commands
    """Build the argument parser for ``wm``."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Waymark keeps a written record of a project in plain markdown and "
            "tells an agent what to do next."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    commands = parser.add_subparsers(title="commands", metavar="<command>")

    summary = "Create the record, or set up this machine in a clone that has one."
    init = commands.add_parser("init", help=summary, description=summary)
    init.add_argument(
        "--atlas",
        metavar="NAME",
        help="make this repository an atlas: a record that several code repos share",
    )
    init.add_argument(
        "--tool",
        action="append",
        metavar="NAME",
        help=f"an agent tool to set up; repeatable (default: {', '.join(adapters.names())})",
    )
    init.add_argument(
        "--yes",
        action="store_true",
        help="ask nothing, even on a terminal: a project with every agent tool, and no CI",
    )
    init.set_defaults(handler=_init)

    summary = "Regenerate the files Waymark owns, and add any missing record folders."
    update = commands.add_parser("update", help=summary, description=summary)
    update.set_defaults(handler=_update)

    _view_command(
        commands, "doctor", _doctor, "Check wm, git and this project's setup; changes nothing."
    )

    summary = "Add a GitHub Actions workflow that installs the pinned wm and runs wm check."
    commands.add_parser("ci", help=summary, description=summary).set_defaults(handler=_ci)
    pr = _view_command(
        commands, "pr", _pr, "Describe a pull request from a change: its title and description."
    )
    pr.add_argument("change", help="the change's name")
    pr.add_argument("--repo", metavar="NAME", help="in an atlas, the code repo it is for")

    summary = "Register atlases on this machine, point code repos at them, check their setup."
    atlas = commands.add_parser("atlas", help=summary, description=summary)
    atlas_commands = atlas.add_subparsers(title="atlas commands", metavar="<command>")
    atlas.set_defaults(handler=lambda _: _usage(atlas))
    summary = (
        "Register this atlas on this machine, with its code repos found through their path "
        "hints, or one code repo at a folder."
    )
    register = atlas_commands.add_parser("register", help=summary, description=summary)
    register.add_argument("repo", nargs="?", help="a code repo's name, from the atlas's settings")
    register.add_argument("folder", nargs="?", help="that code repo's folder")
    register.set_defaults(handler=_atlas_register)
    summary = "Write the pointer file that tells this code repo which atlas holds its record."
    point = atlas_commands.add_parser("point", help=summary, description=summary)
    point.add_argument("atlas", help="the atlas's name")
    point.add_argument(
        "--path", metavar="FOLDER", help="the atlas's folder, relative to this repository's top"
    )
    point.set_defaults(handler=_atlas_point)
    _view_command(
        atlas_commands,
        "doctor",
        _atlas_doctor,
        "Check this atlas's registry entries, code repos, branches and pins; changes nothing.",
    )

    summary = "Answer an agent tool's hook event, read as JSON from standard input."
    hook = commands.add_parser("hook", help=summary, description=summary)
    hook.add_argument("tool", help="the agent tool whose hook this is")
    hook.add_argument("event", help="the tool's name for the event")
    hook.set_defaults(handler=_hook)

    summary = "Create a change, milestone, exploration or resource from the built-in template."
    new = commands.add_parser("new", help=summary, description=summary)
    new.add_argument("kind", choices=["change", "milestone", "exploration", "resource"])
    new.add_argument("name", help="a kebab-case name, for example add-search-limit")
    new.add_argument(
        "resource_kind",
        nargs="?",
        metavar="resource-kind",
        help="for a resource only: service, platform, account, database, dataset or document",
    )
    new.add_argument("--short", action="store_true", help="put a change on the short path")
    new.add_argument("--owner", metavar="NAME", help="a change's owner (default: your git name)")
    new.add_argument(
        "--milestone",
        metavar="MILESTONE",
        help="the milestone a change belongs to; links it from the milestone's roadmap",
    )
    new.add_argument(
        "--after",
        metavar="CHANGE",
        help="the change this one comes after; its unmerged branch is this one's base",
    )
    new.add_argument(
        "--from",
        dest="source",
        metavar="EXPLORATION",
        help="the exploration a change or milestone comes from; its status then leads to it",
    )
    new.set_defaults(handler=_new)

    summary = "Accept a change, so its items can be applied. For the human to run."
    accept = commands.add_parser("accept", help=summary, description=summary)
    accept.add_argument("change", help="the change's name")
    _by(accept)
    accept.set_defaults(handler=_accept)

    _by(_item_command(commands, "tick", _tick, "Tick an item: it has been applied."))
    block = _item_command(commands, "block", _block, "Record that an item is blocked.")
    block.add_argument("reason", help="why it is blocked")
    _by(block)
    gap = _item_command(
        commands, "gap", _gap, "Record a spec gap: the record wasn't enough to build an item."
    )
    gap.add_argument("note", help="what is missing from the record")
    _by(gap)
    note = _item_command(
        commands,
        "note",
        _note,
        "Write a note about an item still to be finished, such as a partial result, in "
        "the change's Log.",
    )
    note.add_argument("text", help="the note")
    _by(note)
    summary = "Record why an accepted change was edited, before the human accepts it again."
    revise = commands.add_parser("revise", help=summary, description=summary)
    revise.add_argument("change", help="the change's name")
    revise.add_argument("why", help="what the edit changed, and why")
    revise.add_argument(
        "--parts",
        metavar="PARTS",
        default="",
        help='the parts it changed, separated by commas: item numbers, "proposal", "design" '
        'or "specs/<area>"',
    )
    _by(revise)
    revise.set_defaults(handler=_revise)
    finding_help = "a finding, written <critical|warning|suggestion>: <place>: <text>; repeatable"
    summary = "Record a self-review of a change, once every item is ticked."
    review = commands.add_parser("review", help=summary, description=summary)
    review.add_argument("change", help="the change's name")
    review.add_argument(
        "--self",
        dest="self_summary",
        metavar="SUMMARY",
        required=True,
        help="what the review checked and found",
    )
    review.add_argument("--finding", action="append", metavar="FINDING", help=finding_help)
    _by(review)
    review.set_defaults(handler=_review)
    summary = "Record a reviewer's verdict on a change."
    verdict = commands.add_parser("verdict", help=summary, description=summary)
    verdict.add_argument("change", help="the change's name")
    verdict.add_argument("verdict", choices=[v.value for v in Verdict])
    verdict.add_argument("reasons", help="the reviewer's reasons")
    verdict.add_argument(
        "--items",
        nargs="+",
        metavar="ITEM",
        help='the items to rebuild; a "changes" verdict names at least one',
    )
    verdict.add_argument("--finding", action="append", metavar="FINDING", help=finding_help)
    _by(verdict)
    verdict.set_defaults(handler=_verdict)
    _by(
        _item_command(
            commands,
            "reopen",
            _reopen,
            "Reopen an item that a review of its change named to rebuild.",
        )
    )
    summary = (
        "Record what was decided about an item or a change's review that went to the human, "
        "and free it."
    )
    resolve = commands.add_parser("resolve", help=summary, description=summary)
    resolve.add_argument("change", help="the change's name")
    resolve.add_argument("item", help="the item's number, or \"review\" for the change's review")
    resolve.add_argument("decision", help="what was decided")
    _by(resolve)
    resolve.set_defaults(handler=_resolve)

    summary = "Merge an applied change's deltas into the specs without archiving it."
    sync = commands.add_parser("sync", help=summary, description=summary)
    sync.add_argument("change", help="the change's name")
    _by(sync)
    sync.set_defaults(handler=_sync)

    summary = "Archive an applied change, once the human says yes."
    archive = commands.add_parser("archive", help=summary, description=summary)
    archive.add_argument("change", help="the change's name")
    archive.add_argument("--built", metavar="TEXT", help="what was built, for the outcome")
    archive.add_argument(
        "--differs",
        metavar="TEXT",
        help="how it differs from the proposal; none when left out",
    )
    archive.add_argument(
        "--override",
        metavar="REASON",
        help="archive although review records are missing; the reason is recorded",
    )
    _by(archive)
    archive.set_defaults(handler=_archive)

    summary = "Close a milestone whose changes are all archived."
    close = commands.add_parser("close", help=summary, description=summary)
    close.add_argument("milestone", help="the milestone's name")
    close.set_defaults(handler=_close)

    summary = "Change a milestone's roadmap: add, drop or move a change's line, with a record."
    roadmap_parser = commands.add_parser("roadmap", help=summary, description=summary)
    roadmap_commands = roadmap_parser.add_subparsers(title="roadmap commands", metavar="<command>")
    roadmap_parser.set_defaults(handler=lambda _: _usage(roadmap_parser))
    summary = "Add a planned line for a change at the end of a milestone's roadmap."
    add = roadmap_commands.add_parser("add", help=summary, description=summary)
    add.add_argument("milestone", help="the milestone's name")
    add.add_argument("change", help="the change's name, for example add-search-limit")
    add.add_argument("description", help="what the change delivers toward the goal")
    _by(add).set_defaults(handler=_roadmap_add)
    summary = "Take a change's line off a milestone's roadmap, with the reason."
    drop = roadmap_commands.add_parser("drop", help=summary, description=summary)
    drop.add_argument("milestone", help="the milestone's name")
    drop.add_argument("change", help="the change's name")
    drop.add_argument("--reason", required=True, help="why the change is dropped")
    _by(drop).set_defaults(handler=_roadmap_drop)
    summary = "Move a change's line on a milestone's roadmap."
    move = roadmap_commands.add_parser("move", help=summary, description=summary)
    move.add_argument("milestone", help="the milestone's name")
    move.add_argument("change", help="the change's name")
    where = move.add_mutually_exclusive_group(required=True)
    where.add_argument("--after", metavar="CHANGE", help="put it right after this change's line")
    where.add_argument("--first", action="store_true", help="put it at the top of the roadmap")
    _by(move).set_defaults(handler=_roadmap_move)

    summary = "End an exploration that won't be acted on: drop it, with the reason."
    exploration_parser = commands.add_parser("exploration", help=summary, description=summary)
    exploration_commands = exploration_parser.add_subparsers(
        title="exploration commands", metavar="<command>"
    )
    exploration_parser.set_defaults(handler=lambda _: _usage(exploration_parser))
    summary = "Drop an open exploration with the reason, and move it to the archive."
    drop_exploration = exploration_commands.add_parser("drop", help=summary, description=summary)
    drop_exploration.add_argument("exploration", help="the exploration's name")
    drop_exploration.add_argument("--reason", required=True, help="why it won't be acted on")
    drop_exploration.set_defaults(handler=_exploration_drop)

    _view_command(
        commands, "status", _status, "Show where things stand: changes, milestones, what needs you."
    )
    _view_command(commands, "inbox", _inbox, "Show what only the human can resolve.")
    show = _view_command(
        commands, "show", _show, "Show everything about one change, spec, milestone or exploration."
    )
    show.add_argument(
        "name", help="its name; an archived change or exploration also by its dated name"
    )
    show.add_argument(
        "--kind", choices=list(payloads.KINDS), help="which kind, if the name is shared"
    )
    show.add_argument(
        "--from",
        dest="source",
        metavar="ATLAS",
        help="read a spec from an atlas this project references",
    )
    ls = _view_command(commands, "ls", _ls, "List changes, specs, milestones or explorations.")
    ls.add_argument("kind", choices=[f"{kind}s" for kind in payloads.KINDS])
    ls.add_argument(
        "--archived",
        action="store_true",
        help="include archived changes, milestones or explorations",
    )
    ls.add_argument(
        "--from",
        dest="source",
        metavar="ATLAS",
        help="list the specs of an atlas this project references",
    )
    instructions = _view_command(
        commands,
        "instructions",
        _instructions,
        "Say what to do at a step of a change: the file, its template, the rules, the commands.",
    )
    instructions.add_argument(
        "step",
        nargs="?",
        choices=[step.value for step in Step],
        help="the step (default: the change's next step)",
    )
    instructions.add_argument("--change", metavar="NAME", help="the change (default: the only one)")
    context = _view_command(
        commands,
        "context",
        _context,
        "Print the context pack for exploring, implementing one item, or reviewing one change.",
    )
    context.add_argument("change", nargs="?", help="the change's name")
    context.add_argument(
        "item", nargs="?", help="the item's number, for example 1.2; none for a review"
    )
    context.add_argument(
        "--for",
        dest="role",
        required=True,
        choices=list(context_service.ROLES),
        help="the job the pack is for",
    )
    check = _view_command(
        commands, "check", _check, "Check the record's health: format, links, conflicts, evidence."
    )
    check.add_argument(
        "--fix",
        action="store_true",
        help="first rewrite the record in its standard layout; wording is never changed",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``wm`` and return its exit code.

    A usage error exits through ``argparse`` with ``EXIT_USAGE``.
    """
    for stream in (sys.stdout, sys.stderr):
        # A console that can't show a character gets a stand-in instead of an error.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Handler | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return EXIT_OK
    take_notices()
    try:
        return handler(args)
    except Refusal as refusal:
        print(f"{PROG}: {refusal}", file=sys.stderr)
        return EXIT_REFUSED
    except Exception as error:
        if handler is not _hook:
            raise
        # A hook that breaks must not stop the agent's work: report it and step aside.
        print(f"{PROG}: the hook failed ({type(error).__name__}: {error})", file=sys.stderr)
        return EXIT_REFUSED
    finally:
        # A hook's reply is the tool's protocol; notices go only to a person at a terminal.
        notices = take_notices()
        if handler is not _hook:
            for note in notices:
                print(f"{PROG}: note: {note}", file=sys.stderr)

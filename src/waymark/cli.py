"""The ``wm`` command: parses arguments, calls services, prints what they return.

This layer stays thin. Every decision is made by a service; a refused command
prints why and what to do next, and exits with ``EXIT_REFUSED``.
"""

import argparse
import datetime
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from waymark import __version__
from waymark.record.terms import Step, Verdict
from waymark.services import context as context_service
from waymark.services import instructions as instructions_service
from waymark.services import lifecycle, setup
from waymark.services.common import Done, Refusal, open_record
from waymark.views import payloads, render
from waymark.views.payloads import Payload
from waymark.views.style import Style

EXIT_OK = 0
"""The command succeeded."""

EXIT_REFUSED = 1
"""The command was refused, or it found problems."""

EXIT_USAGE = 2
"""The command line was wrong."""

PROG = "wm"

Handler = Callable[[argparse.Namespace], int]


def _report(done: Done) -> int:
    print(done.message)
    return EXIT_OK


def _here() -> Path:
    return Path.cwd()


def _today() -> datetime.date:
    return datetime.date.today()


def _init(args: argparse.Namespace) -> int:
    return _report(setup.init_project(_here(), args.atlas))


def _new(args: argparse.Namespace) -> int:
    if args.kind == "change":
        return _report(setup.create_change(_here(), args.name, short=args.short, owner=args.owner))
    if args.short or args.owner:
        raise Refusal("--short and --owner apply to a change only.")
    if args.kind == "milestone":
        return _report(setup.create_milestone(_here(), args.name))
    return _report(setup.create_exploration(_here(), args.name))


def _accept(args: argparse.Namespace) -> int:
    return _report(lifecycle.accept(_here(), args.change, _today()))


def _tick(args: argparse.Namespace) -> int:
    return _report(lifecycle.tick(_here(), args.change, args.item))


def _block(args: argparse.Namespace) -> int:
    return _report(lifecycle.block(_here(), args.change, args.item, args.reason))


def _gap(args: argparse.Namespace) -> int:
    return _report(lifecycle.report_gap(_here(), args.change, args.item, args.note))


def _review(args: argparse.Namespace) -> int:
    done = lifecycle.self_review(_here(), args.change, args.item, args.self_summary, _today())
    return _report(done)


def _verdict(args: argparse.Namespace) -> int:
    result = Verdict(args.verdict)
    done = lifecycle.verdict(_here(), args.change, args.item, result, args.reasons, _today())
    return _report(done)


def _reopen(args: argparse.Namespace) -> int:
    return _report(lifecycle.reopen(_here(), args.change, args.item, _today()))


def _resolve(args: argparse.Namespace) -> int:
    return _report(lifecycle.resolve(_here(), args.change, args.item, args.decision, _today()))


def _sync(args: argparse.Namespace) -> int:
    return _report(lifecycle.sync(_here(), args.change, _today()))


def _archive(args: argparse.Namespace) -> int:
    done = lifecycle.archive(
        _here(), args.change, _today(), outcome=args.outcome, override=args.override
    )
    return _report(done)


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
    _show_payload(payloads.show(open_record(_here()), args.name, args.kind), args)
    return EXIT_OK


def _ls(args: argparse.Namespace) -> int:
    kind = args.kind.removesuffix("s")
    _show_payload(payloads.ls(open_record(_here()), kind, archived=args.archived), args)
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
    now = datetime.datetime.now(datetime.UTC)
    payload = payloads.check(open_record(_here()), now)
    _show_payload(payload, args)
    return EXIT_REFUSED if payload["errors"] else EXIT_OK


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

    summary = "Create the record in this git repository."
    init = commands.add_parser("init", help=summary, description=summary)
    init.add_argument(
        "--atlas",
        metavar="NAME",
        help="make this repository an atlas: a record that several code repos share",
    )
    init.set_defaults(handler=_init)

    summary = "Create a change, milestone or exploration from the built-in template."
    new = commands.add_parser("new", help=summary, description=summary)
    new.add_argument("kind", choices=["change", "milestone", "exploration"])
    new.add_argument("name", help="a kebab-case name, for example add-search-limit")
    new.add_argument("--short", action="store_true", help="put a change on the short path")
    new.add_argument("--owner", metavar="NAME", help="a change's owner (default: your git name)")
    new.set_defaults(handler=_new)

    summary = "Accept a change, so its items can be applied. For the human to run."
    accept = commands.add_parser("accept", help=summary, description=summary)
    accept.add_argument("change", help="the change's name")
    accept.set_defaults(handler=_accept)

    _item_command(commands, "tick", _tick, "Tick an item: it has been applied.")
    block = _item_command(commands, "block", _block, "Record that an item is blocked.")
    block.add_argument("reason", help="why it is blocked")
    gap = _item_command(
        commands, "gap", _gap, "Record a spec gap: the record wasn't enough to build an item."
    )
    gap.add_argument("note", help="what is missing from the record")
    review = _item_command(commands, "review", _review, "Record a self-review of an item.")
    review.add_argument(
        "--self",
        dest="self_summary",
        metavar="SUMMARY",
        required=True,
        help="what the review checked and found",
    )
    verdict = _item_command(
        commands, "verdict", _verdict, "Record a reviewer's verdict on an item."
    )
    verdict.add_argument("verdict", choices=[v.value for v in Verdict])
    verdict.add_argument("reasons", help="the reviewer's reasons")
    _item_command(commands, "reopen", _reopen, "Reopen an item after a review asked for changes.")
    resolve = _item_command(
        commands,
        "resolve",
        _resolve,
        "Record what was decided about an item that went to the human, and free it.",
    )
    resolve.add_argument("decision", help="what was decided")

    summary = "Merge an applied change's deltas into the specs without archiving it."
    sync = commands.add_parser("sync", help=summary, description=summary)
    sync.add_argument("change", help="the change's name")
    sync.set_defaults(handler=_sync)

    summary = "Archive an applied change. For the human to run."
    archive = commands.add_parser("archive", help=summary, description=summary)
    archive.add_argument("change", help="the change's name")
    archive.add_argument("--outcome", metavar="TEXT", help="what came of the change")
    archive.add_argument(
        "--override",
        metavar="REASON",
        help="archive although review records are missing; the reason is recorded",
    )
    archive.set_defaults(handler=_archive)

    summary = "Close a milestone whose changes are all archived."
    close = commands.add_parser("close", help=summary, description=summary)
    close.add_argument("milestone", help="the milestone's name")
    close.set_defaults(handler=_close)

    _view_command(
        commands, "status", _status, "Show where things stand: changes, milestones, what needs you."
    )
    _view_command(commands, "inbox", _inbox, "Show what only the human can resolve.")
    show = _view_command(
        commands, "show", _show, "Show everything about one change, spec, milestone or exploration."
    )
    show.add_argument("name", help="its name; an archived change also by its dated folder name")
    show.add_argument(
        "--kind", choices=list(payloads.KINDS), help="which kind, if the name is shared"
    )
    ls = _view_command(commands, "ls", _ls, "List changes, specs, milestones or explorations.")
    ls.add_argument("kind", choices=[f"{kind}s" for kind in payloads.KINDS])
    ls.add_argument(
        "--archived", action="store_true", help="include archived changes or milestones"
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
        "Print the context pack for exploring, or for implementing or reviewing one item.",
    )
    context.add_argument("change", nargs="?", help="the change's name")
    context.add_argument("item", nargs="?", help="the item's number, for example 1.2")
    context.add_argument(
        "--for",
        dest="role",
        required=True,
        choices=list(context_service.ROLES),
        help="the job the pack is for",
    )
    _view_command(
        commands, "check", _check, "Check the record's health: format, links, conflicts, evidence."
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
    try:
        return handler(args)
    except Refusal as refusal:
        print(f"{PROG}: {refusal}", file=sys.stderr)
        return EXIT_REFUSED

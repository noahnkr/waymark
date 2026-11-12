"""The ``wm`` command: parses arguments, calls services, prints what they return.

This layer stays thin. Every decision is made by a service; a refused command
prints why and what to do next, and exits with ``EXIT_REFUSED``.
"""

import argparse
import datetime
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from waymark import __version__
from waymark.record.terms import Verdict
from waymark.services import check as check_service
from waymark.services import lifecycle, setup
from waymark.services.common import Done, Refusal

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


def _check(_: argparse.Namespace) -> int:
    now = datetime.datetime.now(datetime.UTC)
    findings = check_service.check(_here(), now)
    for finding in findings:
        where = finding.path + (f":{finding.line}" if finding.line else "")
        print(f"{finding.severity.value}: {where}: {finding.code}: {finding.message}")
    errors = sum(1 for f in findings if f.severity is check_service.Severity.ERROR)
    warnings = len(findings) - errors
    if not findings:
        print("The record is healthy.")
    else:
        print(f"{errors} error(s), {warnings} warning(s).")
    return EXIT_REFUSED if errors else EXIT_OK


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


def build_parser() -> argparse.ArgumentParser:
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

    summary = "Check the record's health: format, links, conflicts and evidence."
    check = commands.add_parser("check", help=summary, description=summary)
    check.set_defaults(handler=_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``wm`` and return its exit code.

    A usage error exits through ``argparse`` with ``EXIT_USAGE``.
    """
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

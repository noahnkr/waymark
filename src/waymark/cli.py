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
from waymark.record.terms import Step, Verdict
from waymark.services import atlas as atlas_service
from waymark.services import ci as ci_service
from waymark.services import context as context_service
from waymark.services import doctor as doctor_service
from waymark.services import githooks as githooks_service
from waymark.services import instructions as instructions_service
from waymark.services import integration, lifecycle, references, setup
from waymark.services import pr as pr_service
from waymark.services.common import Done, Refusal, open_record, take_notices
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
    if done.message:
        print(done.message)
    return EXIT_OK


def _here() -> Path:
    return Path.cwd()


def _today() -> datetime.date:
    return datetime.date.today()


def _init(args: argparse.Namespace) -> int:
    tools = tuple(args.tool) if args.tool else None
    return _report(setup.init_project(_here(), args.atlas, tools))


def _update(_: argparse.Namespace) -> int:
    return _report(integration.update(_here()))


def _atlas_register(args: argparse.Namespace) -> int:
    if (args.repo is None) != (args.folder is None):
        raise Refusal("Give both the code repo's name and its folder, or neither.")
    return _report(atlas_service.register(_here(), args.repo, args.folder))


def _atlas_point(args: argparse.Namespace) -> int:
    return _report(atlas_service.point(_here(), args.atlas, args.path))


def _git_hooks(_: argparse.Namespace) -> int:
    return _report(githooks_service.git_hooks(_here()))


def _run_hook(args: argparse.Namespace) -> int:
    if args.name == "commit-msg":
        if not args.file:
            raise Refusal("The commit-msg hook needs the commit message file git passes it.")
        return _report(githooks_service.check_commit_message(_here(), args.file))
    now = datetime.datetime.now(datetime.UTC)
    return _report(githooks_service.check_staged_record(_here(), now))


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
    init.add_argument(
        "--tool",
        action="append",
        metavar="NAME",
        help=f"an agent tool to set up; repeatable (default: {', '.join(adapters.names())})",
    )
    init.set_defaults(handler=_init)

    summary = "Migrate the record to this version and regenerate the files Waymark owns."
    update = commands.add_parser("update", help=summary, description=summary)
    update.set_defaults(handler=_update)

    _view_command(
        commands, "doctor", _doctor, "Check wm, git and this project's setup; changes nothing."
    )

    summary = "Put the committed git hooks in this repository and point this clone's git at them."
    commands.add_parser("git-hooks", help=summary, description=summary).set_defaults(
        handler=_git_hooks
    )
    summary = "Run one of the git hooks' checks; the hooks call this."
    run_hook = commands.add_parser("run-hook", help=summary, description=summary)
    run_hook.add_argument("name", choices=list(githooks_service.HOOK_NAMES))
    run_hook.add_argument("file", nargs="?", help="the commit message file (commit-msg only)")
    run_hook.set_defaults(handler=_run_hook)
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
    show.add_argument(
        "--from",
        dest="source",
        metavar="ATLAS",
        help="read a spec from an atlas this project references",
    )
    ls = _view_command(commands, "ls", _ls, "List changes, specs, milestones or explorations.")
    ls.add_argument("kind", choices=[f"{kind}s" for kind in payloads.KINDS])
    ls.add_argument(
        "--archived", action="store_true", help="include archived changes or milestones"
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

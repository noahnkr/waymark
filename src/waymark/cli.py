"""The ``wm`` command: parses arguments, calls services, renders output.

This layer stays thin. It has no commands yet; it only answers ``--help`` and
``--version`` and fixes the exit-code contract every later command follows.
"""

import argparse
from collections.abc import Sequence

from waymark import __version__

EXIT_OK = 0
"""The command succeeded."""

EXIT_REFUSED = 1
"""The command was refused, or it found problems."""

EXIT_USAGE = 2
"""The command line was wrong."""

PROG = "wm"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``wm``."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Waymark keeps a written record of a project in plain markdown and "
            "tells an agent what to do next."
        ),
        epilog="No commands are available yet.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``wm`` and return its exit code.

    A usage error exits through ``argparse`` with ``EXIT_USAGE``.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return EXIT_OK

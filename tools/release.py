"""Checks a release tag before anything is published, and prints its release notes.

    python -m tools.release check v0.1.0   # refuse unless everything is ready
    python -m tools.release notes v0.1.0   # the changelog's entry for that version

Run by the release workflow. It only reads files.
"""

import re
import sys
from pathlib import Path

from waymark import __version__

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
PENDING = "pending the 0.1.0 smoke test"
_HEADING = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<date>.+)$", re.MULTILINE)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def entry(changelog: str, version: str) -> str | None:
    """A version's entry in the changelog, heading included; None when there is none."""
    headings = list(_HEADING.finditer(changelog))
    for index, heading in enumerate(headings):
        if heading["version"] == version:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
            return changelog[heading.start() : end].strip() + "\n"
    return None


def problems(tag: str, version: str, changelog: str, readme: str) -> list[str]:
    """Why a tag can't be released; empty when it can."""
    found = []
    if tag != f"v{version}":
        found.append(f"The tag {tag} doesn't match the package version {version} (tag v{version}).")
    if ".dev" in version:
        found.append(f"{version} is a development version. Set the release version first.")
    text = entry(changelog, version)
    if text is None:
        found.append(f'CHANGELOG.md has no "## [{version}] - <date>" entry.')
    else:
        heading = _HEADING.match(text)
        if heading is None or not _DATE.match(heading["date"].strip()):
            found.append(f"The changelog entry for {version} has no release date (YYYY-MM-DD).")
        if "Smoke test:" not in text:
            found.append(f"The changelog entry for {version} doesn't record the smoke test result.")
    if PENDING in readme:
        found.append("The README still says the Claude Code version is pending the smoke test.")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("check", "notes"):  # noqa: PLR2004 - command and tag
        print("usage: python -m tools.release check|notes <tag>", file=sys.stderr)
        return 2
    command, tag = argv
    changelog = CHANGELOG.read_text(encoding="utf-8")
    if command == "notes":
        text = entry(changelog, tag.removeprefix("v"))
        if text is None:
            print(f"CHANGELOG.md has no entry for {tag}.", file=sys.stderr)
            return 1
        print(text, end="")
        return 0
    found = problems(tag, __version__, changelog, README.read_text(encoding="utf-8"))
    for problem in found:
        print(problem, file=sys.stderr)
    if not found:
        print(f"{tag} is ready to release.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

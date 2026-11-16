"""The migration from record format 2 to 3: what humans write takes its new layout.

wm reads only format 3, so this migration reads the old files as text, with its
own few patterns. Wording never changes; only the layout does:

- every proposal, active and archived, gets its ``Owner:``, ``Review:`` and
  ``Path:`` facts as bullets;
- a build tag at the end of an item line becomes a ``- Build: delegate`` line,
  the item's last sub-line;
- every delta's section headings become ``## ADDED Requirements`` and the like;
- the charter's glossary lines ``<term>: <meaning>`` become
  ``- **<term>**: <meaning>``, and its step headings are capitalized;
- every exploration gets a ``- Status:`` line from its Conclusion: ``parked``
  for a ``Parked:`` conclusion, whose reason stays as the Conclusion,
  ``led-to`` with the link for a linked one, and ``open`` otherwise.
"""

import re
from collections.abc import Callable

from waymark.record.files import RecordFiles
from waymark.record.store import Transaction
from waymark.record.terms import Step

CHANGES = "changes"
ARCHIVE = "archive"
EXPLORATIONS = "explorations"
CHARTER = "charter.md"

_FACT = re.compile(r"^(Owner|Review|Path):[ \t]")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_ITEM = re.compile(r"^- \[[ xX]\] \d+\.\d+\s")
_BUILD_TAG = re.compile(r"\s+`build:\s*([A-Za-z-]+)`")
_DELTA_HEADINGS = {
    "added requirements": "ADDED Requirements",
    "modified requirements": "MODIFIED Requirements",
    "removed requirements": "REMOVED Requirements",
}
_GLOSSARY_LINE = re.compile(r"^([A-Z][^:*]*?):\s+(\S.*)$")
_PARKED = re.compile(r"^Parked:\s*(.*)$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def migrate_to_format_3(files: RecordFiles, transaction: Transaction) -> None:
    """Stage the format 3 text of every change, the charter and every exploration."""

    def rewrite(path: str, change: Callable[[str], str]) -> None:
        if not files.is_file(path):
            return
        text = files.read(path, [])
        if text is None:
            return
        new = change(text)
        if new != text:
            transaction.write(path, new)

    for folder in _change_folders(files):
        rewrite(f"{folder}/proposal.md", _proposal)
        rewrite(f"{folder}/tasks.md", _tasks)
        for entry in files.entries(f"{folder}/specs"):
            if not entry.is_dir and entry.name.endswith(".md"):
                rewrite(f"{folder}/specs/{entry.name}", _delta)
    rewrite(CHARTER, _charter)
    for entry in files.entries(EXPLORATIONS):
        if not entry.is_dir and entry.name.endswith(".md"):
            rewrite(f"{EXPLORATIONS}/{entry.name}", _exploration)


def _change_folders(files: RecordFiles) -> list[str]:
    folders = [
        f"{CHANGES}/{entry.name}"
        for entry in files.entries(CHANGES)
        if entry.is_dir and entry.name != ARCHIVE
    ]
    folders += [
        f"{CHANGES}/{ARCHIVE}/{entry.name}"
        for entry in files.entries(f"{CHANGES}/{ARCHIVE}")
        if entry.is_dir
    ]
    return folders


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _bare(line: str) -> str:
    return line.rstrip("\r\n")


def _ending(line: str) -> str:
    return line[len(_bare(line)) :]


def _fenced(lines: list[str]) -> list[bool]:
    """Which lines sit in fenced code."""
    flags: list[bool] = []
    fence: str | None = None
    for line in lines:
        stripped = line.strip()
        marker = stripped[:3] if stripped[:3] in ("```", "~~~") else None
        if fence is None and marker:
            fence = marker
            flags.append(True)
        elif fence is not None:
            flags.append(True)
            if marker == fence:
                fence = None
        else:
            flags.append(False)
    return flags


def _proposal(text: str) -> str:
    """Facts between the title and the first section become bullets."""
    lines = _lines(text)
    in_preamble = False
    for index, line in enumerate(lines):
        heading = _HEADING.match(_bare(line))
        if heading:
            if len(heading.group(1)) == 1 and not in_preamble:
                in_preamble = True
                continue
            break
        if in_preamble and _FACT.match(line):
            lines[index] = f"- {line}"
    return "".join(lines)


def _tasks(text: str) -> str:
    """A trailing build tag becomes the item's last sub-line."""
    lines = _lines(text)
    fenced = _fenced(lines)
    out: list[str] = []
    pending: str | None = None
    for index, line in enumerate(lines):
        bare = _bare(line)
        starts_block = not line.startswith(" ") and bool(bare.strip())
        if pending is not None and (starts_block or not bare.strip()):
            out.append(pending)
            pending = None
        if not fenced[index] and _ITEM.match(bare) and (tag := _BUILD_TAG.search(bare)):
            out.append(bare[: tag.start()] + bare[tag.end() :] + _ending(line))
            pending = f"  - Build: {tag.group(1)}{_ending(line) or chr(10)}"
            continue
        out.append(line)
    if pending is not None:
        if out and not out[-1].endswith(("\n", "\r")):
            out[-1] += "\n"
        out.append(pending)
    return "".join(out)


def _delta(text: str) -> str:
    """The section headings take their upper-case names."""
    lines = _lines(text)
    fenced = _fenced(lines)
    for index, line in enumerate(lines):
        heading = _HEADING.match(_bare(line))
        if fenced[index] or heading is None or heading.group(1) != "##":
            continue
        new = _DELTA_HEADINGS.get(heading.group(2).casefold())
        if new is not None:
            lines[index] = f"## {new}{_ending(line)}"
    return "".join(lines)


def _charter(text: str) -> str:
    """Glossary lines become a bold-term list, and step headings are capitalized."""
    lines = _lines(text)
    fenced = _fenced(lines)
    section = ""
    steps = {step.value for step in Step}
    in_comment = False
    for index, line in enumerate(lines):
        bare = _bare(line)
        if fenced[index]:
            continue
        if in_comment or bare.lstrip().startswith("<!--"):
            in_comment = "-->" not in bare
            continue
        heading = _HEADING.match(bare)
        if heading:
            if heading.group(1) == "##":
                section = heading.group(2).casefold()
            elif heading.group(1) == "###" and heading.group(2).casefold() in steps:
                lines[index] = f"### {heading.group(2).capitalize()}{_ending(line)}"
            continue
        glossary = _GLOSSARY_LINE.match(bare)
        if section == "glossary" and glossary:
            lines[index] = f"- **{glossary.group(1)}**: {glossary.group(2)}{_ending(line)}"
    return "".join(lines)


def _exploration(text: str) -> str:
    """A status line under the title, from the Conclusion; "Parked:" comes off its reason."""
    lines = _lines(text)
    title = next((i for i, line in enumerate(lines) if _bare(line).startswith("# ")), None)
    if title is None or any(_bare(line).startswith("- Status:") for line in lines):
        return text
    newline = _ending(lines[title]) or "\n"
    conclusion = next(
        (i for i, line in enumerate(lines) if _bare(line).strip().casefold() == "## conclusion"),
        None,
    )
    status = "open"
    if conclusion is not None:
        body = []
        for index in range(conclusion + 1, len(lines)):
            if _bare(lines[index]).startswith("## "):
                break
            body.append(index)
        written = [
            i
            for i in body
            if _bare(lines[i]).strip() and not _bare(lines[i]).lstrip().startswith("<!--")
        ]
        first = written[0] if written else None
        parked = _PARKED.match(_bare(lines[first]).strip()) if first is not None else None
        link = next(
            (
                match
                for i in written
                for match in _LINK.finditer(lines[i])
                if f"{CHANGES}/" in match.group(2) or "milestones/" in match.group(2)
            ),
            None,
        )
        if parked is not None and first is not None:
            status = "parked"
            lines[first] = parked.group(1) + _ending(lines[first])
        elif link is not None:
            status = f"led-to [{link.group(1)}]({link.group(2)})"
    lines[title + 1 : title + 1] = [newline, f"- Status: {status}{newline}"]
    return "".join(lines)

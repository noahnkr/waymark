"""The standard layout of a record file: what ``wm check --fix`` writes.

The layout never touches wording. Outside fenced code and comments it:

- turns the list markers ``*`` and ``+`` into ``-``;
- leaves one blank line before each heading, and at most one after it;
- takes trailing spaces off every line;
- re-renders each record and finding wm owns into its standard shape;

and it ends the file with exactly one line break. Each line keeps its line
ending; a line it adds takes the file's. Running it twice gives the same text,
and the acceptance fingerprint is taken over this layout, so fixing the layout
never withdraws an acceptance.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from waymark.record.evidence import records
from waymark.record.markdown.text import BOM, Document

_MARKER = re.compile(r"^(\s*)[*+](\s+\S.*)$")
_THEMATIC_BREAK = re.compile(r"^\s*([*+-])(\s*\1){2,}\s*$")
_RECORD_LINE = re.compile(r"^(\s*- )(\(.*)$")
_FINDING_LINE = re.compile(r"^(\s+- )((?:critical|warning|suggestion) .*)$")
_COMMENT_OPEN = "<!--"
_COMMENT_CLOSE = "-->"


class Fix(StrEnum):
    """A kind of layout fix, as ``wm check --fix`` reports it."""

    LIST_MARKERS = "list markers"
    HEADING_SPACING = "blank lines around headings"
    TRAILING_SPACES = "trailing spaces"
    FINAL_LINE_BREAK = "the final line break"
    RECORD_LINES = "record lines"


@dataclass
class _Line:
    text: str
    ending: str
    protected: bool
    """In fenced code or a comment: left exactly as it is."""
    heading: bool = False

    @property
    def blank(self) -> bool:
        return not self.protected and not self.text.strip()


def _comment_flags(doc: Document) -> list[bool]:
    """Which lines sit in a comment, outside fenced code."""
    flags: list[bool] = []
    open_comment = False
    for line in doc.lines:
        if line.in_fence:
            flags.append(False)
            continue
        text = line.text
        starts = open_comment or _COMMENT_OPEN in text
        flags.append(starts)
        if open_comment:
            open_comment = _COMMENT_CLOSE not in text
        elif _COMMENT_OPEN in text:
            after = text[text.index(_COMMENT_OPEN) :]
            open_comment = _COMMENT_CLOSE not in after
    return flags


def _fix_line(text: str, fixes: set[Fix]) -> str:
    """One unprotected line in its standard layout."""
    stripped = text.rstrip(" \t")
    if stripped != text:
        fixes.add(Fix.TRAILING_SPACES)
    marker = _MARKER.match(stripped)
    if marker and not _THEMATIC_BREAK.match(stripped):
        stripped = f"{marker.group(1)}-{marker.group(2)}"
        fixes.add(Fix.LIST_MARKERS)
    record_line = _RECORD_LINE.match(stripped)
    if record_line:
        found = records.parse(record_line.group(2))
        if isinstance(found, records.Record):
            rendered = record_line.group(1) + records.render(found)
            if rendered != stripped:
                fixes.add(Fix.RECORD_LINES)
            return rendered
    finding_line = _FINDING_LINE.match(stripped)
    if finding_line:
        finding = records.parse_finding(finding_line.group(2))
        if finding is not None:
            rendered = finding_line.group(1) + records.render_finding(finding)
            if rendered != stripped:
                fixes.add(Fix.RECORD_LINES)
            return rendered
    return stripped


def _space_headings(lines: list[_Line], newline: str) -> list[_Line]:
    """One blank line before each heading, and at most one after it.

    No blank line is added after a heading, so a requirement or a scenario
    keeps its text directly under it.
    """
    out: list[_Line] = []
    after_heading = False
    for line in lines:
        if line.heading:
            while out and out[-1].blank:
                out.pop()
            if out:
                out.append(_Line("", newline, protected=False))
            out.append(line)
            after_heading = True
        elif line.blank and after_heading:
            if not out[-1].blank:
                out.append(line)
        else:
            after_heading = False
            out.append(line)
    return out


def standard_layout(text: str) -> tuple[str, tuple[Fix, ...]]:
    """The text in its standard layout, and the kinds of fix that took."""
    if not text:
        return text, ()
    doc = Document.parse("", text)
    newline = doc.newline
    in_comment = _comment_flags(doc)
    heading_rows = {heading.index for heading in doc.headings}
    fixes: set[Fix] = set()
    lines: list[_Line] = []
    for index, line in enumerate(doc.lines):
        protected = line.in_fence or in_comment[index]
        fixed = line.text if protected else _fix_line(line.text, fixes)
        heading = index in heading_rows and not protected
        lines.append(_Line(fixed, line.ending, protected, heading))

    spaced = _space_headings(lines, newline)

    def rows(found: list[_Line]) -> list[tuple[str, str]]:
        return [(line.text, line.ending) for line in found]

    if rows(spaced) != rows(lines):
        fixes.add(Fix.HEADING_SPACING)

    ending_before = len(spaced)
    while spaced and spaced[-1].blank:
        spaced.pop()
    if spaced and (len(spaced) != ending_before or not spaced[-1].ending):
        fixes.add(Fix.FINAL_LINE_BREAK)
        spaced[-1].ending = spaced[-1].ending or newline

    body = "".join(line.text + line.ending for line in spaced)
    result = (BOM if doc.bom else "") + body
    if result == text:
        return text, ()
    return result, tuple(fix for fix in Fix if fix in fixes)

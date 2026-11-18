"""Markdown as wm reads it: lines with their endings, fences, headings, sections, links.

A document keeps every line's text and line ending apart, so a later write can
change the lines it owns and put everything else back byte for byte.
"""

import re
from dataclasses import dataclass

BOM = "﻿"

_LINE_BREAK = re.compile(r"\r\n|\n|\r")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CODE_SPAN = re.compile(r"(`+).+?\1")
_INLINE_LINK = re.compile(r"\]\(\s*<?([^()\s<>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_REFERENCE_LINK = re.compile(r"^ {0,3}\[[^\]^][^\]]*\]:\s*<?([^\s<>]+)>?")


@dataclass(frozen=True)
class Line:
    """One line: its text, its line ending, and whether it is inside a code fence."""

    text: str
    ending: str
    in_fence: bool

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()


@dataclass(frozen=True)
class Heading:
    """A heading: its level, its title, and the index of its line."""

    level: int
    title: str
    index: int


@dataclass(frozen=True)
class Section:
    """A heading and the lines under it, up to the next heading of its level or above."""

    heading: Heading
    end: int

    @property
    def title(self) -> str:
        return self.heading.title

    @property
    def start(self) -> int:
        return self.heading.index

    @property
    def body_start(self) -> int:
        return self.heading.index + 1


@dataclass(frozen=True)
class Link:
    """A link target, with the line and the span where the target is written."""

    index: int
    start: int
    end: int
    target: str


def _track_fence(text: str, fence: str | None) -> tuple[bool, str | None]:
    """Whether a line is part of a code fence, and the fence still open after it."""
    match = _FENCE.match(text)
    if fence is None:
        return (True, match.group(1)) if match else (False, None)
    closes = (
        match is not None
        and match.group(1)[0] == fence[0]
        and len(match.group(1)) >= len(fence)
        and text.strip() == match.group(1)
    )
    return True, None if closes else fence


@dataclass(frozen=True, eq=False)
class Document:
    """A markdown file, split into lines and outlined by its headings.

    ``path`` is relative to the record's root, with forward slashes.
    """

    path: str
    text: str
    bom: bool
    lines: tuple[Line, ...]
    headings: tuple[Heading, ...]

    @classmethod
    def parse(cls, path: str, text: str) -> "Document":
        bom = text.startswith(BOM)
        body = text[1:] if bom else text
        lines: list[Line] = []
        fence: str | None = None
        position = 0
        for match in _LINE_BREAK.finditer(body):
            in_fence, fence = _track_fence(body[position : match.start()], fence)
            lines.append(Line(body[position : match.start()], match.group(), in_fence))
            position = match.end()
        if position < len(body):
            in_fence, fence = _track_fence(body[position:], fence)
            lines.append(Line(body[position:], "", in_fence))
        headings = [
            Heading(len(found.group(1)), found.group(2), index)
            for index, line in enumerate(lines)
            if not line.in_fence and (found := _HEADING.match(line.text))
        ]
        return cls(path, text, bom, tuple(lines), tuple(headings))

    @property
    def newline(self) -> str:
        """The file's line ending: that of its first line, or LF for a one-line file."""
        for line in self.lines:
            if line.ending:
                return line.ending
        return "\n"

    @property
    def title(self) -> Heading | None:
        """The first level-1 heading."""
        return next((heading for heading in self.headings if heading.level == 1), None)

    @property
    def preamble(self) -> tuple[int, int]:
        """The line range between the title and the next heading."""
        title = self.title
        start = 0 if title is None else title.index + 1
        end = next((h.index for h in self.headings if h.index >= start), len(self.lines))
        return start, end

    def raw_lines(self) -> list[str]:
        """Every line with its ending; joined, they give back the file's exact text."""
        raw = [line.text + line.ending for line in self.lines]
        if self.bom:
            if raw:
                raw[0] = BOM + raw[0]
            else:
                raw.append(BOM)
        return raw

    def sections(self, level: int, start: int = 0, end: int | None = None) -> tuple[Section, ...]:
        """The sections of one heading level whose headings lie in a line range."""
        stop = len(self.lines) if end is None else end
        inside = [heading for heading in self.headings if start <= heading.index < stop]
        found: list[Section] = []
        for position, heading in enumerate(inside):
            if heading.level != level:
                continue
            later = (h.index for h in inside[position + 1 :] if h.level <= level)
            found.append(Section(heading, next(later, stop)))
        return tuple(found)

    def content_end(self, start: int, end: int) -> int:
        """The index after the last non-blank line in a range; ``start`` if all are blank."""
        last = end
        while last > start and self.lines[last - 1].is_blank:
            last -= 1
        return last

    def text_between(self, start: int, end: int) -> str:
        """The text of a line range, without HTML comments or surrounding blank lines.

        Lines are joined with LF whatever the file's line endings are.
        """
        joined = "\n".join(line.text for line in self.lines[start:end])
        return _COMMENT.sub("", joined).strip()

    def body(self, section: Section) -> str:
        """A section's text under its heading."""
        return self.text_between(section.body_start, section.end)

    def links(self) -> tuple[Link, ...]:
        """Every link target outside code fences and code spans."""
        found: list[Link] = []
        for index, line in enumerate(self.lines):
            if line.in_fence:
                continue
            reference = _REFERENCE_LINK.match(line.text)
            if reference:
                found.append(Link(index, reference.start(1), reference.end(1), reference.group(1)))
                continue
            code = [match.span() for match in _CODE_SPAN.finditer(line.text)]
            for match in _INLINE_LINK.finditer(line.text):
                if not any(start <= match.start() < end for start, end in code):
                    found.append(Link(index, match.start(1), match.end(1), match.group(1)))
        return tuple(found)

"""The marked block wm keeps in a repository's ``.gitignore``.

The block lists the files wm writes for one machine, so they stay out of git.
It sits between two marker lines, and wm only ever changes what is between
them: every other line of the file comes back byte for byte, with its line
ending. Everything here is text in, text out.
"""

from collections.abc import Sequence

from waymark.record.markdown.text import BOM, Document

PATH = ".gitignore"
BEGIN = "# Waymark: this machine's agent tool files and git hooks, written by wm"
END = "# end of Waymark"


def render(patterns: Sequence[str], newline: str = "\n") -> str:
    """The block: the opening marker, one pattern per line, and the closing marker."""
    return "".join(f"{line}{newline}" for line in (BEGIN, *patterns, END))


def _block(doc: Document) -> tuple[int, int] | None:
    """The line range of the block, end exclusive, or None when the file has none.

    A block whose closing marker is missing runs to the first blank line, so
    the lines a project wrote after it are kept.
    """
    lines = doc.lines
    start = next((i for i, line in enumerate(lines) if line.text.rstrip() == BEGIN), None)
    if start is None:
        return None
    for index in range(start + 1, len(lines)):
        if lines[index].text.rstrip() == END:
            return start, index + 1
        if lines[index].is_blank:
            return start, index
    return start, len(lines)


def merged(current: str | None, patterns: Sequence[str]) -> str:
    """The file's text with the block for these patterns, added at the end or replaced in place.

    ``current`` is None when the file doesn't exist. The block takes the file's
    line ending. When the block is already current, the text comes back unchanged.
    """
    if not current:
        return render(patterns)
    doc = Document.parse(PATH, current)
    newline = doc.newline
    raw = doc.raw_lines()
    block = _block(doc)
    if block is None:
        if doc.lines and not doc.lines[-1].ending:
            raw[-1] += newline
        if doc.lines and not doc.lines[-1].is_blank:
            raw.append(newline)
        return "".join(raw) + render(patterns, newline)
    start, end = block
    lines = render(patterns, newline).splitlines(keepends=True)
    if end == len(doc.lines) and not doc.lines[-1].ending:
        lines[-1] = lines[-1][: -len(newline)]
    if doc.bom and start == 0:
        lines[0] = BOM + lines[0]
    raw[start:end] = lines
    return "".join(raw)

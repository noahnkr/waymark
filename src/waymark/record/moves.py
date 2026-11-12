"""Moving a folder inside the record, and rewriting the links the move would break."""

import posixpath
import re
from urllib.parse import quote

from waymark.record.edits import replace_spans
from waymark.record.links import local_path, resolve
from waymark.record.text import Document

_UNCHECKED = re.compile(r"^(\s*[-*]\s+)\[ \]")


def _inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(f"{folder}/")


def _retarget(original: str, new_path: str) -> str:
    """A link's new target: the new path, with the original's anchor and style kept."""
    path = local_path(original) or ""
    suffix = original[len(original.split("#", 1)[0].split("?", 1)[0]) :]
    if path.endswith("/") and not new_path.endswith("/"):
        new_path += "/"
    if "%" in original:
        new_path = quote(new_path)
    return new_path + suffix


def rewrite_links(doc: Document, source: str, target: str) -> str:
    """A document's text after the folder ``source`` has moved to ``target``.

    Links that point into the moved folder follow it. If the document itself is
    in the moved folder, its links to everything outside are re-aimed from its
    new place. Links wm doesn't follow (web addresses, anchors) are left alone.
    """
    moving = _inside(doc.path, source)
    new_doc_path = target + doc.path[len(source) :] if moving else doc.path
    replacements: dict[tuple[int, int, int], str] = {}
    for link in doc.links():
        resolved = resolve(doc.path, link.target)
        if resolved is None:
            continue
        points_inside = _inside(resolved, source)
        if points_inside == moving:
            continue
        destination = target + resolved[len(source) :] if points_inside else resolved
        relative = posixpath.relpath(destination, posixpath.dirname(new_doc_path) or ".")
        replacements[(link.index, link.start, link.end)] = _retarget(link.target, relative)
    return replace_spans(doc, replacements) if replacements else doc.text


def tick_roadmap_lines(doc: Document, folder: str) -> str:
    """A roadmap's text with the lines that link into a folder ticked."""
    replacements: dict[tuple[int, int, int], str] = {}
    for link in doc.links():
        resolved = resolve(doc.path, link.target)
        match = _UNCHECKED.match(doc.lines[link.index].text)
        if resolved is not None and _inside(resolved, folder) and match:
            replacements[(link.index, match.end(1), match.end())] = "[x]"
    return replace_spans(doc, replacements) if replacements else doc.text

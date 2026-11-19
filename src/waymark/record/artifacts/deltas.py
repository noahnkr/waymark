"""Deltas: a change's edits to one spec, and how they merge into it.

A delta adds, modifies, removes or renames requirements. It may also carry the
spec's title, purpose, background and repos; it must carry the purpose when it creates the
spec. A rename keeps the requirement's statement and scenarios; the same delta
may also modify the requirement under its new name.
"""

from dataclasses import dataclass

from waymark.record.artifacts.specs import (
    BACKGROUND,
    PURPOSE,
    REPOS_FACT,
    REQUIREMENTS,
    Requirement,
    Spec,
    empty_background,
    named_blocks,
    parse_requirements,
    parse_spec,
    requirement_key,
)
from waymark.record.markdown import labels
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.outline import (
    collect_sections,
    parse_facts,
    require_title,
    split_names,
)
from waymark.record.markdown.problems import Problem
from waymark.record.markdown.text import Document

ADDED = "ADDED Requirements"
MODIFIED = "MODIFIED Requirements"
REMOVED = "REMOVED Requirements"
RENAMED = "RENAMED Requirements"


@dataclass(frozen=True)
class Rename:
    """A requirement a delta renames, keeping its statement and scenarios."""

    old: str
    new: str
    index: int

    @property
    def old_key(self) -> str:
        return requirement_key(self.old)

    @property
    def new_key(self) -> str:
        return requirement_key(self.new)


@dataclass(frozen=True)
class Removal:
    """A requirement a delta removes, and why."""

    name: str
    reason: str
    index: int

    @property
    def key(self) -> str:
        return requirement_key(self.name)


@dataclass(frozen=True)
class Delta:
    """A change's edits to one spec."""

    domain: str
    doc: Document
    title: str
    repos: tuple[str, ...] | None
    purpose: str | None
    added: tuple[Requirement, ...]
    modified: tuple[Requirement, ...]
    removed: tuple[Removal, ...]
    problems: tuple[Problem, ...]
    renamed: tuple[Rename, ...] = ()
    background: str | None = None

    def touched(self) -> tuple[tuple[str, str], ...]:
        """The key and name of every requirement this delta adds, modifies, removes or renames."""
        named = [(item.key, item.name) for item in (*self.added, *self.modified)]
        named += [(item.key, item.name) for item in self.removed]
        for rename in self.renamed:
            named += [(rename.old_key, rename.old), (rename.new_key, rename.new)]
        return tuple(dict.fromkeys(named))

    def based_on(self) -> tuple[str, ...]:
        """The names, as the spec now has them, of the requirements this delta builds on."""
        renamed = {rename.new_key: rename.old for rename in self.renamed}
        names = [renamed.get(item.key, item.name) for item in self.modified]
        names += [item.name for item in self.removed]
        names += [rename.old for rename in self.renamed]
        return tuple(dict.fromkeys(names))


@dataclass(frozen=True)
class Merge:
    """The result of merging a delta: the spec's new text, or why it doesn't apply."""

    text: str | None
    problems: tuple[Problem, ...]


def _reason(text: str) -> labels.Label | None:
    """A removal's ``Reason:`` line, when it has text."""
    label = labels.read_label(text)
    if label is None or label.name != labels.REASON or not label.value:
        return None
    return label


def _parse_removals(doc: Document, problems: list[Problem]) -> tuple[Removal, ...]:
    sections = {section.title.casefold(): section for section in doc.sections(2)}
    parent = sections.get(REMOVED.casefold())
    if parent is None:
        return ()
    removals: list[Removal] = []
    for name, section in named_blocks(doc, parent, problems):
        lines = doc.lines[section.body_start : section.end]
        reason = next((label.value for line in lines if (label := _reason(line.text))), "")
        if not reason:
            problems.append(
                Problem(
                    doc.path,
                    section.start + 1,
                    "removal-without-reason",
                    f'Removing "{name}" needs a reason. Add a '
                    f'"{label_line(labels.REASON, "<why>", bullet=False)}" line under it.',
                )
            )
        removals.append(Removal(name, reason, section.start))
    return tuple(removals)


def _parse_renames(doc: Document, problems: list[Problem]) -> tuple[Rename, ...]:
    sections = {section.title.casefold(): section for section in doc.sections(2)}
    parent = sections.get(RENAMED.casefold())
    if parent is None:
        return ()
    renames: list[Rename] = []
    pending: tuple[str, int] | None = None
    for index in range(parent.body_start, parent.end):
        line = doc.lines[index]
        if line.is_blank or line.in_fence:
            continue
        match = labels.read_label(line.text)
        if (
            match is None
            or not match.bullet
            or match.name not in (labels.FROM, labels.TO)
            or not match.value
        ):
            problems.append(
                Problem(
                    doc.path,
                    index + 1,
                    "malformed-rename",
                    f'A rename is a "{label_line(labels.FROM, "<old name>")}" line followed by a '
                    f'"{label_line(labels.TO, "<new name>")}" line.',
                )
            )
            continue
        word, name = match.name, match.value
        if word == labels.FROM:
            if pending is not None:
                problems.append(_unpaired(doc, pending[1]))
            pending = (name, index)
        elif pending is None:
            problems.append(_unpaired(doc, index))
        else:
            renames.append(Rename(pending[0], name, pending[1]))
            pending = None
    if pending is not None:
        problems.append(_unpaired(doc, pending[1]))
    return tuple(renames)


def _unpaired(doc: Document, index: int) -> Problem:
    return Problem(
        doc.path,
        index + 1,
        "malformed-rename",
        f'Every "{label_line(labels.FROM)}" line is followed by its own '
        f'"{label_line(labels.TO)}" line.',
    )


def parse_delta(domain: str, doc: Document) -> Delta:
    """Read a delta file."""
    problems: list[Problem] = []
    title = require_title(doc, problems)
    facts = parse_facts(doc, {REPOS_FACT}, problems, prose=False)
    repos: tuple[str, ...] | None = None
    if REPOS_FACT in facts:
        repos = split_names(facts[REPOS_FACT].value)
        if not repos:
            problems.append(
                Problem(
                    doc.path,
                    facts[REPOS_FACT].index + 1,
                    "empty-fact",
                    f'"{label_line(REPOS_FACT, bullet=False)}" names no repo. List the repos, '
                    "or remove the line.",
                )
            )
    for section in doc.sections(2):
        heading = section.title.strip()
        for name in (ADDED, MODIFIED, REMOVED, RENAMED):
            if heading.casefold() == name.casefold() and heading != name:
                problems.append(
                    Problem(
                        doc.path,
                        section.start + 1,
                        "layout",
                        f'A delta section is headed "## {name}", written exactly so.',
                    )
                )
    sections = collect_sections(
        doc,
        (),
        problems,
        optional=(PURPOSE, BACKGROUND, ADDED, MODIFIED, REMOVED, RENAMED),
        strict=True,
    )
    purpose: str | None = None
    if PURPOSE in sections:
        purpose = doc.body(sections[PURPOSE])
        if not purpose:
            problems.append(
                Problem(
                    doc.path,
                    sections[PURPOSE].start + 1,
                    "empty-section",
                    f'"## {PURPOSE}" is empty. Write the purpose, or remove the section.',
                )
            )
    background: str | None = None
    if BACKGROUND in sections:
        background = doc.body(sections[BACKGROUND])
        if not background:
            problems.append(empty_background(doc, sections[BACKGROUND]))
    added = parse_requirements(doc, sections[ADDED], problems) if ADDED in sections else ()
    modified = parse_requirements(doc, sections[MODIFIED], problems) if MODIFIED in sections else ()
    removed = _parse_removals(doc, problems)
    renamed = _parse_renames(doc, problems)

    new_names = {rename.new_key for rename in renamed}
    named = [(item.key, item.name) for item in added]
    named += [(item.key, item.name) for item in modified if item.key not in new_names]
    named += [(item.key, item.name) for item in removed]
    named += [(rename.old_key, rename.old) for rename in renamed]
    named += [(rename.new_key, rename.new) for rename in renamed]
    seen: set[str] = set()
    for key, name in named:
        if key in seen:
            problems.append(
                Problem(
                    doc.path,
                    1,
                    "duplicate-requirement",
                    f'Requirement "{name}" appears more than once in this delta. '
                    "Keep one operation for it.",
                )
            )
        seen.add(key)
    if not seen and purpose is None and background is None and repos is None:
        problems.append(
            Problem(
                doc.path,
                1,
                "empty-delta",
                f'The delta changes nothing. Add a "## {ADDED}", "## {MODIFIED}", '
                f'"## {REMOVED}" or "## {RENAMED}" section with at least one requirement.',
            )
        )
    return Delta(
        domain,
        doc,
        title,
        repos,
        purpose,
        added,
        modified,
        removed,
        tuple(problems),
        renamed,
        background,
    )


def delta_mismatches(spec: Spec | None, delta: Delta) -> tuple[Problem, ...]:
    """Why a delta doesn't apply to the spec as it now stands; empty when it does."""
    path = delta.doc.path
    problems: list[Problem] = []
    if spec is not None and spec.problems:
        return (
            Problem(
                path,
                1,
                "spec-unreadable",
                f'The spec "{spec.domain}" has format problems, so no delta can merge into it. '
                "Fix the spec first.",
            ),
        )
    if spec is None and delta.purpose is None:
        problems.append(
            Problem(
                path,
                1,
                "delta-without-purpose",
                f'This delta creates the spec "{delta.domain}", so it must say what the spec '
                f'is for. Add a "## {PURPOSE}" section.',
            )
        )
    for requirement in delta.added:
        if spec is not None and spec.requirement(requirement.name) is not None:
            problems.append(
                Problem(
                    path,
                    requirement.start + 1,
                    "delta-requirement-exists",
                    f'The spec already has a requirement "{requirement.name}". '
                    f'Move it under "## {MODIFIED}", or rename it.',
                )
            )
    for rename in delta.renamed:
        if spec is not None and spec.requirement(rename.new) is not None:
            problems.append(
                Problem(
                    path,
                    rename.index + 1,
                    "delta-requirement-exists",
                    f'The spec already has a requirement "{rename.new}", so "{rename.old}" '
                    "can't be renamed to it.",
                )
            )
    new_names = {rename.new_key for rename in delta.renamed}
    changed = [(item.name, item.start) for item in delta.modified if item.key not in new_names]
    changed += [(item.name, item.index) for item in delta.removed]
    changed += [(rename.old, rename.index) for rename in delta.renamed]
    for name, index in changed:
        if spec is None or spec.requirement(name) is None:
            problems.append(
                Problem(
                    path,
                    index + 1,
                    "delta-requirement-missing",
                    f'The spec "{delta.domain}" has no requirement "{name}" to modify, '
                    f"remove or rename. Update the delta to match the spec, or move it under "
                    f'"## {ADDED}".',
                )
            )
    return tuple(problems)


def delta_is_merged(spec: Spec | None, delta: Delta) -> bool:
    """Whether the spec already reads the way the delta says it should."""
    if spec is None or spec.problems:
        return False
    for requirement in (*delta.added, *delta.modified):
        living = spec.requirement(requirement.name)
        if living is None or living.block != requirement.block:
            return False
    if any(spec.requirement(removal.name) is not None for removal in delta.removed):
        return False
    for rename in delta.renamed:
        if spec.requirement(rename.old) is not None or spec.requirement(rename.new) is None:
            return False
    wholes = ((delta.purpose, spec.purpose), (delta.background, spec.background))
    if any(wanted is not None and wanted != living for wanted, living in wholes):
        return False
    return delta.repos is None or spec.repos == delta.repos


def _new_spec_text(delta: Delta) -> str:
    newline = delta.doc.newline
    lines = [f"# {delta.title}", ""]
    if delta.repos:
        lines += [label_line(REPOS_FACT, ", ".join(delta.repos), bullet=False), ""]
    lines += [f"## {PURPOSE}", "", *(delta.purpose or "").split("\n"), ""]
    if delta.background is not None:
        lines += [f"## {BACKGROUND}", "", *delta.background.split("\n"), ""]
    lines += [f"## {REQUIREMENTS}"]
    for requirement in delta.added:
        lines += ["", *requirement.block]
    return newline.join(lines) + newline


def _reparse(spec: Spec, lines: list[str]) -> Document:
    return Document.parse(spec.doc.path, "".join(lines))


def _replace_and_remove(spec: Spec, delta: Delta, lines: list[str], newline: str) -> None:
    edits: list[tuple[int, int, list[str]]] = []
    renamed = {rename.new_key: rename.old for rename in delta.renamed}
    modified = {item.key for item in delta.modified}
    for rename in delta.renamed:
        if rename.new_key in modified:
            continue
        target = spec.requirement(rename.old)
        assert target is not None
        # Rebuilt rather than edited: the spec's heading may spell the old name in
        # another case or spacing, which the lookup ignores.
        hashes = target.block[0].split(maxsplit=1)[0]
        heading = f"{hashes} Requirement: {rename.new}"
        edits.append((target.start, target.start + 1, [heading + newline]))
    for requirement in delta.modified:
        target = spec.requirement(renamed.get(requirement.key, requirement.name))
        assert target is not None
        edits.append((target.start, target.end, [text + newline for text in requirement.block]))
    for removal in delta.removed:
        target = spec.requirement(removal.name)
        assert target is not None
        edits.append((target.start, target.extent_end, []))
    for start, end, replacement in sorted(edits, key=lambda edit: edit[0], reverse=True):
        lines[start:end] = replacement


def _append_added(spec: Spec, delta: Delta, lines: list[str], newline: str) -> None:
    doc = _reparse(spec, lines)
    section = next(s for s in doc.sections(2) if s.title.casefold() == REQUIREMENTS.casefold())
    position = doc.content_end(section.start, section.end)
    new: list[str] = []
    for requirement in delta.added:
        new += [newline, *(text + newline for text in requirement.block)]
    lines[position:position] = new


def _set_body(spec: Spec, name: str, body: str, lines: list[str], newline: str) -> None:
    """Replace the body of the spec's ``## <name>`` section, keeping its heading."""
    doc = _reparse(spec, lines)
    section = next(s for s in doc.sections(2) if s.title.casefold() == name.casefold())
    end = doc.content_end(section.body_start, section.end)
    start = section.body_start
    while start < end and doc.lines[start].is_blank:
        start += 1
    lines[start:end] = [text + newline for text in body.split("\n")]


def _set_background(spec: Spec, background: str, lines: list[str], newline: str) -> None:
    """Replace the spec's Background, or insert one right before its Requirements."""
    doc = _reparse(spec, lines)
    sections = {s.title.casefold(): s for s in doc.sections(2)}
    if BACKGROUND.casefold() in sections:
        _set_body(spec, BACKGROUND, background, lines, newline)
        return
    position = sections[REQUIREMENTS.casefold()].start
    body = [text + newline for text in background.split("\n")]
    lines[position:position] = [f"## {BACKGROUND}{newline}", newline, *body, newline]


def _set_repos(spec: Spec, repos: tuple[str, ...], lines: list[str], newline: str) -> None:
    doc = _reparse(spec, lines)
    fact_line = label_line(REPOS_FACT, ", ".join(repos), bullet=False) + newline
    facts = parse_facts(doc, {REPOS_FACT}, [], prose=True)
    if REPOS_FACT in facts:
        index = facts[REPOS_FACT].index
        lines[index : index + 1] = [fact_line]
    else:
        title = doc.title
        assert title is not None
        lines[title.index + 1 : title.index + 1] = [newline, fact_line]


def merge_delta(spec: Spec | None, delta: Delta) -> Merge:
    """Merge a delta into its spec, or create the spec when there is none.

    Only the lines of the requirements the delta names change; every other line
    of the spec, and its line endings, stay as they are.
    """
    problems = (*delta.problems, *delta_mismatches(spec, delta))
    if problems:
        return Merge(None, tuple(problems))
    if spec is None:
        return Merge(_new_spec_text(delta), ())

    newline = spec.doc.newline
    lines = spec.doc.raw_lines()
    if lines and not spec.doc.lines[-1].ending:
        lines[-1] += newline
    _replace_and_remove(spec, delta, lines, newline)
    if delta.added:
        _append_added(spec, delta, lines, newline)
    if delta.purpose is not None:
        _set_body(spec, PURPOSE, delta.purpose, lines, newline)
    if delta.background is not None:
        _set_background(spec, delta.background, lines, newline)
    if delta.repos is not None:
        _set_repos(spec, delta.repos, lines, newline)
    while len(lines) > 1 and not lines[-1].strip():
        lines.pop()

    text = "".join(lines)
    merged = parse_spec(spec.domain, Document.parse(spec.doc.path, text))
    if merged.problems:
        return Merge(None, merged.problems)
    return Merge(text, ())

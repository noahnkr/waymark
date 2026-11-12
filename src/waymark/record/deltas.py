"""Deltas: a change's edits to one spec, and how they merge into it.

A delta adds, modifies or removes requirements. It may also carry the spec's
title, purpose and repos; it must carry the purpose when it creates the spec.
"""

import re
from dataclasses import dataclass

from waymark.record.outline import collect_sections, parse_facts, require_title, split_names
from waymark.record.problems import Problem
from waymark.record.specs import (
    PURPOSE,
    REPOS_FACT,
    REQUIREMENTS,
    Requirement,
    Spec,
    named_blocks,
    parse_requirements,
    parse_spec,
    requirement_key,
)
from waymark.record.text import Document

ADDED = "Added requirements"
MODIFIED = "Modified requirements"
REMOVED = "Removed requirements"

_REASON = re.compile(r"^Reason:\s*(\S.*)$")


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

    def touched(self) -> tuple[tuple[str, str], ...]:
        """The key and name of every requirement this delta adds, modifies or removes."""
        named = [(item.key, item.name) for item in (*self.added, *self.modified)]
        named += [(item.key, item.name) for item in self.removed]
        return tuple(named)


@dataclass(frozen=True)
class Merge:
    """The result of merging a delta: the spec's new text, or why it doesn't apply."""

    text: str | None
    problems: tuple[Problem, ...]


def _parse_removals(doc: Document, problems: list[Problem]) -> tuple[Removal, ...]:
    sections = {section.title.casefold(): section for section in doc.sections(2)}
    parent = sections.get(REMOVED.casefold())
    if parent is None:
        return ()
    removals: list[Removal] = []
    for name, section in named_blocks(doc, parent, problems):
        lines = doc.lines[section.body_start : section.end]
        reason = next((m.group(1).strip() for line in lines if (m := _REASON.match(line.text))), "")
        if not reason:
            problems.append(
                Problem(
                    doc.path,
                    section.start + 1,
                    "removal-without-reason",
                    f'Removing "{name}" needs a reason. Add a "Reason: <why>" line under it.',
                )
            )
        removals.append(Removal(name, reason, section.start))
    return tuple(removals)


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
                    f'"{REPOS_FACT}:" names no repo. List the repos, or remove the line.',
                )
            )
    sections = collect_sections(
        doc, (), problems, optional=(PURPOSE, ADDED, MODIFIED, REMOVED), strict=True
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
    added = parse_requirements(doc, sections[ADDED], problems) if ADDED in sections else ()
    modified = parse_requirements(doc, sections[MODIFIED], problems) if MODIFIED in sections else ()
    removed = _parse_removals(doc, problems)

    named = [(item.key, item.name) for item in (*added, *modified)]
    named += [(item.key, item.name) for item in removed]
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
    if not seen and purpose is None and repos is None:
        problems.append(
            Problem(
                doc.path,
                1,
                "empty-delta",
                f'The delta changes nothing. Add a "## {ADDED}", "## {MODIFIED}" or '
                f'"## {REMOVED}" section with at least one requirement.',
            )
        )
    return Delta(domain, doc, title, repos, purpose, added, modified, removed, tuple(problems))


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
    changed = [(item.name, item.start) for item in delta.modified]
    changed += [(item.name, item.index) for item in delta.removed]
    for name, index in changed:
        if spec is None or spec.requirement(name) is None:
            problems.append(
                Problem(
                    path,
                    index + 1,
                    "delta-requirement-missing",
                    f'The spec "{delta.domain}" has no requirement "{name}" to modify or '
                    f'remove. Update the delta to match the spec, or move it under "## {ADDED}".',
                )
            )
    return tuple(problems)


def _new_spec_text(delta: Delta) -> str:
    newline = delta.doc.newline
    lines = [f"# {delta.title}", ""]
    if delta.repos:
        lines += [f"{REPOS_FACT}: {', '.join(delta.repos)}", ""]
    lines += [f"## {PURPOSE}", "", *(delta.purpose or "").split("\n"), "", f"## {REQUIREMENTS}"]
    for requirement in delta.added:
        lines += ["", *requirement.block]
    return newline.join(lines) + newline


def _reparse(spec: Spec, lines: list[str]) -> Document:
    return Document.parse(spec.doc.path, "".join(lines))


def _replace_and_remove(spec: Spec, delta: Delta, lines: list[str], newline: str) -> None:
    edits: list[tuple[int, int, list[str]]] = []
    for requirement in delta.modified:
        target = spec.requirement(requirement.name)
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


def _set_purpose(spec: Spec, purpose: str, lines: list[str], newline: str) -> None:
    doc = _reparse(spec, lines)
    section = next(s for s in doc.sections(2) if s.title.casefold() == PURPOSE.casefold())
    end = doc.content_end(section.body_start, section.end)
    start = section.body_start
    while start < end and doc.lines[start].is_blank:
        start += 1
    lines[start:end] = [text + newline for text in purpose.split("\n")]


def _set_repos(spec: Spec, repos: tuple[str, ...], lines: list[str], newline: str) -> None:
    doc = _reparse(spec, lines)
    fact_line = f"{REPOS_FACT}: {', '.join(repos)}{newline}"
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
        _set_purpose(spec, delta.purpose, lines, newline)
    if delta.repos is not None:
        _set_repos(spec, delta.repos, lines, newline)
    while len(lines) > 1 and not lines[-1].strip():
        lines.pop()

    text = "".join(lines)
    merged = parse_spec(spec.domain, Document.parse(spec.doc.path, text))
    if merged.problems:
        return Merge(None, merged.problems)
    return Merge(text, ())

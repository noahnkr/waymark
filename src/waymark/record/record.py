"""The record as a whole: every artifact, read fresh from the files.

Active artifacts are parsed when the record is loaded. Archived changes are
only listed; each is parsed when something asks for it.
"""

import datetime
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from waymark.record.artifacts.changes import PROPOSAL_FILE, SPECS_DIR, Change, load_change
from waymark.record.artifacts.charter import CHARTER_FILE, Charter, parse_charter
from waymark.record.artifacts.config import CONFIG_FILE, Config, parse_config
from waymark.record.artifacts.explorations import Exploration, parse_exploration
from waymark.record.artifacts.milestones import (
    MILESTONE_FILE,
    Goal,
    Milestone,
    Roadmap,
    parse_milestone,
)
from waymark.record.artifacts.proposal import parse_proposal
from waymark.record.artifacts.resources import Resource, parse_resource, unknown_specs
from waymark.record.artifacts.specs import Spec, parse_spec
from waymark.record.machine.files import RecordFiles
from waymark.record.machine.project import Project
from waymark.record.markdown.links import LinkChecker
from waymark.record.markdown.problems import WHOLE_FILE, Problem
from waymark.record.markdown.text import Document
from waymark.record.names import NAME_RULE, is_valid_name, parse_archive_name
from waymark.record.terms import Layout, ReviewLevel

SPECS = "specs"
CHANGES = "changes"
MILESTONES = "milestones"
EXPLORATIONS = "explorations"
RESOURCES = "resources"
ARCHIVE = "archive"

FOLDER_KEEP = ".gitkeep"
"""The empty file that keeps a record folder in git while it holds nothing else."""

RECORD_FOLDERS = (
    SPECS,
    CHANGES,
    f"{CHANGES}/{ARCHIVE}",
    EXPLORATIONS,
    f"{EXPLORATIONS}/{ARCHIVE}",
    MILESTONES,
    f"{MILESTONES}/{ARCHIVE}",
    RESOURCES,
)
"""The record's folders, each kept in git by a ``.gitkeep``."""


@dataclass(frozen=True, order=True)
class ArchiveEntry:
    """An archived folder: the date it was archived, its name and where it is."""

    date: datetime.date
    name: str
    path: str


@dataclass(frozen=True)
class HistoryEntry:
    """An archived change that touched a spec, with its outcome."""

    date: datetime.date
    change: str
    outcome: str | None


@dataclass(frozen=True)
class Record:
    """Everything in the record, as the files now stand."""

    project: Project
    config: Config | None
    charter: Charter | None
    specs: Mapping[str, Spec]
    changes: Mapping[str, Change]
    archived_changes: tuple[ArchiveEntry, ...]
    milestones: Mapping[str, Milestone]
    archived_milestones: tuple[ArchiveEntry, ...]
    explorations: Mapping[str, Exploration]
    problems: tuple[Problem, ...]
    resources: Mapping[str, Resource] = field(default_factory=dict)
    archived_explorations: tuple[ArchiveEntry, ...] = ()

    @property
    def files(self) -> RecordFiles:
        return RecordFiles(self.project.record_root)

    @property
    def default_review(self) -> ReviewLevel:
        return self.config.default_review if self.config else ReviewLevel.SELF

    @property
    def layout(self) -> Layout:
        return self.config.layout if self.config else Layout.REPO

    def documents(self) -> Iterator[Document]:
        """Every parsed markdown file of the active record."""
        if self.charter:
            yield self.charter.doc
        for spec in self.specs.values():
            yield spec.doc
        for change in self.changes.values():
            if change.proposal:
                yield change.proposal.doc
            for delta in change.deltas.values():
                yield delta.doc
            if change.design:
                yield change.design.doc
            if change.tasks:
                yield change.tasks.doc
        for milestone in self.milestones.values():
            if milestone.goal:
                yield milestone.goal.doc
        for exploration in self.explorations.values():
            yield exploration.doc
        for resource in self.resources.values():
            yield resource.doc


def _bad_name(path: str, kind: str) -> Problem:
    return Problem(
        path,
        WHOLE_FILE,
        "invalid-name",
        f"A {kind} is named in {NAME_RULE}. Rename it.",
    )


def _load_config(files: RecordFiles, problems: list[Problem]) -> Config | None:
    text = files.read(CONFIG_FILE, problems)
    if text is None:
        return None
    config, found = parse_config(text)
    problems.extend(found)
    return config


def _load_charter(files: RecordFiles, problems: list[Problem]) -> Charter | None:
    if not files.is_file(CHARTER_FILE):
        problems.append(
            Problem(
                CHARTER_FILE,
                WHOLE_FILE,
                "missing-file",
                "The record has no charter. Create it from the built-in template.",
            )
        )
        return None
    doc = files.document(CHARTER_FILE, problems)
    if doc is None:
        return None
    charter = parse_charter(doc)
    problems.extend(charter.problems)
    return charter


def _load_markdown_folder(
    files: RecordFiles, folder: str, kind: str, problems: list[Problem]
) -> dict[str, Document]:
    documents: dict[str, Document] = {}
    for entry in files.entries(folder):
        relative = f"{folder}/{entry.name}"
        name = entry.name.removesuffix(".md")
        if folder == EXPLORATIONS and entry.is_dir and entry.name == ARCHIVE:
            continue
        if entry.is_dir or not entry.name.endswith(".md"):
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unexpected-file",
                    f'"{folder}/" holds one <name>.md file per {kind}. Move this elsewhere '
                    "or remove it.",
                )
            )
        elif not is_valid_name(name):
            problems.append(_bad_name(relative, kind))
        else:
            doc = files.document(relative, problems)
            if doc is not None:
                documents[name] = doc
    return documents


def _split_folder(
    files: RecordFiles, folder: str, kind: str, problems: list[Problem]
) -> tuple[list[str], list[ArchiveEntry]]:
    """The active and archived folders under ``changes/`` or ``milestones/``."""
    active: list[str] = []
    archived: list[ArchiveEntry] = []
    for entry in files.entries(folder):
        relative = f"{folder}/{entry.name}"
        if not entry.is_dir:
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unexpected-file",
                    f'"{folder}/" holds one folder per {kind}. Move this file into one, '
                    "or remove it.",
                )
            )
        elif entry.name == ARCHIVE:
            continue
        elif is_valid_name(entry.name):
            active.append(entry.name)
        else:
            problems.append(_bad_name(relative, kind))
    for entry in files.entries(f"{folder}/{ARCHIVE}"):
        relative = f"{folder}/{ARCHIVE}/{entry.name}"
        parsed = parse_archive_name(entry.name) if entry.is_dir else None
        if parsed is None:
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "invalid-name",
                    f"An archived {kind} is a folder named YYYY-MM-DD-<name>. The archive is "
                    "written by wm; rename this to match, or remove it.",
                )
            )
        else:
            archived.append(ArchiveEntry(parsed.date, parsed.name, relative))
    return active, sorted(archived)


def _load_milestone(files: RecordFiles, name: str, path: str, problems: list[Problem]) -> Milestone:
    found: list[Problem] = []
    goal: Goal | None = None
    roadmap: Roadmap | None = None
    for entry in files.entries(path):
        relative = f"{path}/{entry.name}"
        if entry.is_dir or entry.name != MILESTONE_FILE:
            found.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unexpected-file",
                    f"A milestone holds {MILESTONE_FILE}. Move this elsewhere or remove it.",
                )
            )
            continue
        doc = files.document(relative, found)
        if doc is not None:
            goal, roadmap = parse_milestone(doc)
            found.extend(goal.problems)
    if goal is None and not files.is_file(f"{path}/{MILESTONE_FILE}"):
        found.append(
            Problem(
                f"{path}/{MILESTONE_FILE}",
                WHOLE_FILE,
                "missing-file",
                f"The milestone has no {MILESTONE_FILE}. Create it from the built-in template.",
            )
        )
    problems.extend(found)
    return Milestone(name, path, goal, roadmap, tuple(sorted(found)))


def _check_spec_repos(spec: Spec, config: Config | None, problems: list[Problem]) -> None:
    if config is None:
        return
    for repo in spec.repos:
        if repo not in config.repo_names:
            known = ", ".join(sorted(config.repo_names)) or "none"
            problems.append(
                Problem(
                    spec.doc.path,
                    WHOLE_FILE,
                    "unknown-repo",
                    f'The spec names the repo "{repo}", which the settings don\'t list '
                    f"(repos: {known}).",
                )
            )


def load_record(project: Project) -> Record:
    """Read the whole active record. Nothing is cached; every call reads the files."""
    files = RecordFiles(project.record_root)
    problems: list[Problem] = []
    config = _load_config(files, problems)
    charter = _load_charter(files, problems)

    specs: dict[str, Spec] = {}
    for name, doc in _load_markdown_folder(files, SPECS, "spec", problems).items():
        specs[name] = parse_spec(name, doc)
        problems.extend(specs[name].problems)
        _check_spec_repos(specs[name], config, problems)

    change_names, archived_changes = _split_folder(files, CHANGES, "change", problems)
    changes: dict[str, Change] = {}
    for name in change_names:
        changes[name] = load_change(files, f"{CHANGES}/{name}", name, config)
        problems.extend(changes[name].problems)

    milestone_names, archived_milestones = _split_folder(files, MILESTONES, "milestone", problems)
    milestones = {
        name: _load_milestone(files, name, f"{MILESTONES}/{name}", problems)
        for name in milestone_names
    }

    explorations: dict[str, Exploration] = {}
    for name, doc in _load_markdown_folder(files, EXPLORATIONS, "exploration", problems).items():
        explorations[name] = parse_exploration(name, doc)
        problems.extend(explorations[name].problems)

    archived_explorations = _archived_files(files, EXPLORATIONS, "exploration", problems)

    resources: dict[str, Resource] = {}
    for name, doc in _load_markdown_folder(files, RESOURCES, "resource", problems).items():
        resources[name] = parse_resource(name, doc)
        problems.extend(resources[name].problems)
        problems.extend(unknown_specs(resources[name], specs))

    return Record(
        project=project,
        config=config,
        charter=charter,
        specs=specs,
        changes=changes,
        archived_changes=tuple(archived_changes),
        milestones=milestones,
        archived_milestones=tuple(archived_milestones),
        explorations=explorations,
        problems=tuple(sorted(problems)),
        resources=resources,
        archived_explorations=tuple(archived_explorations),
    )


def _archived_files(
    files: RecordFiles, folder: str, kind: str, problems: list[Problem]
) -> list[ArchiveEntry]:
    """The archived files under ``<folder>/archive/``, each named ``YYYY-MM-DD-<name>.md``."""
    archived: list[ArchiveEntry] = []
    for entry in files.entries(f"{folder}/{ARCHIVE}"):
        relative = f"{folder}/{ARCHIVE}/{entry.name}"
        stem = entry.name.removesuffix(".md")
        parsed = None if entry.is_dir or stem == entry.name else parse_archive_name(stem)
        if parsed is None:
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "invalid-name",
                    f"An archived {kind} is a file named YYYY-MM-DD-<name>.md. The archive is "
                    "written by wm; rename this to match, or remove it.",
                )
            )
        else:
            archived.append(ArchiveEntry(parsed.date, parsed.name, relative))
    return sorted(archived)


def load_archived_exploration(record: Record, entry: ArchiveEntry) -> Exploration | None:
    """Read one archived exploration, as it was written; None when it can't be read."""
    doc = record.files.document(entry.path, [])
    return parse_exploration(entry.name, doc) if doc is not None else None


def load_archived_change(record: Record, entry: ArchiveEntry) -> Change:
    """Read one archived change."""
    return load_change(record.files, entry.path, entry.name, record.config, entry.date)


def spec_history(record: Record, domain: str) -> tuple[HistoryEntry, ...]:
    """The archived changes whose deltas touched a spec, oldest first, with their outcomes."""
    files = record.files
    history: list[HistoryEntry] = []
    for entry in record.archived_changes:
        if not files.is_file(f"{entry.path}/{SPECS_DIR}/{domain}.md"):
            continue
        doc = files.document(f"{entry.path}/{PROPOSAL_FILE}", [])
        outcome = parse_proposal(doc).outcome if doc else None
        history.append(HistoryEntry(entry.date, entry.name, outcome))
    return tuple(history)


def link_problems(record: Record) -> tuple[Problem, ...]:
    """Every broken or non-portable link in the active record."""
    checker = LinkChecker(record.project.record_root)
    found: list[Problem] = []
    for doc in record.documents():
        found.extend(checker.problems(doc))
    return tuple(sorted(found))

"""Changes: one folder per unit of work, holding its proposal, deltas, design and tasks."""

import datetime
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.config import Config
from waymark.record.deltas import Delta, parse_delta
from waymark.record.design import Design, parse_design
from waymark.record.files import RecordFiles
from waymark.record.names import NAME_RULE, is_valid_name
from waymark.record.problems import WHOLE_FILE, Problem
from waymark.record.proposal import (
    ACCEPTED,
    PATH,
    REVIEW,
    SHORT,
    SYNCED,
    Acceptance,
    Proposal,
    parse_proposal,
)
from waymark.record.records import RecordKind
from waymark.record.tasks import LATEST_FORMAT, LOG_SECTION, Tasks, parse_tasks
from waymark.record.terms import Layout, ReviewLevel
from waymark.record.text import Document

PROPOSAL_FILE = "proposal.md"
DESIGN_FILE = "design.md"
TASKS_FILE = "tasks.md"
SPECS_DIR = "specs"


@dataclass(frozen=True)
class Change:
    """A change folder and what is in it.

    ``problems`` holds every problem in the change's files; each one's path
    says which file it belongs to.
    """

    name: str
    path: str
    archived_on: datetime.date | None
    proposal: Proposal | None
    deltas: Mapping[str, Delta]
    design: Design | None
    tasks: Tasks | None
    problems: tuple[Problem, ...]
    version: int = 1
    """The record format the change was read in."""

    @property
    def acceptance(self) -> Acceptance | None:
        """The acceptance that counts: the latest ``(accepted)`` record, or the old line."""
        if self.version < LATEST_FORMAT:
            return self.proposal.acceptance if self.proposal else None
        if self.tasks is None:
            return None
        record = self.tasks.latest(RecordKind.ACCEPTED)
        if record is None or record.fingerprint is None:
            return None
        fingerprint = record.fingerprint
        synced = self.tasks.latest(RecordKind.SYNCED)
        if synced is not None and synced.fingerprint and synced.index > record.index:
            fingerprint = synced.fingerprint
        return Acceptance(record.date, record.who or "", fingerprint, record.index, record.covers)

    @property
    def synced(self) -> datetime.date | None:
        """When the change's deltas were merged into the specs, if they were."""
        if self.version < LATEST_FORMAT:
            return self.proposal.synced if self.proposal else None
        record = self.tasks.latest(RecordKind.SYNCED) if self.tasks else None
        return record.date if record else None

    @property
    def short_path(self) -> bool:
        return self.proposal is not None and self.proposal.short_path

    def review_level(self, default: ReviewLevel) -> ReviewLevel:
        """The change's review level: its proposal's Review line, or the project default."""
        if self.proposal is not None and self.proposal.review is not None:
            return self.proposal.review
        return default

    def problems_in(self, relative: str) -> tuple[Problem, ...]:
        """The problems in one file or folder of the change."""
        target = f"{self.path}/{relative}"
        return tuple(
            problem
            for problem in self.problems
            if problem.path == target or problem.path.startswith(f"{target}/")
        )


def _load_deltas(files: RecordFiles, path: str, problems: list[Problem]) -> dict[str, Delta]:
    deltas: dict[str, Delta] = {}
    for entry in files.entries(f"{path}/{SPECS_DIR}"):
        relative = f"{path}/{SPECS_DIR}/{entry.name}"
        domain = entry.name.removesuffix(".md")
        if entry.is_dir or not entry.name.endswith(".md") or not is_valid_name(domain):
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unexpected-file",
                    f"A change's specs folder holds one <domain>.md delta per spec, named in "
                    f"{NAME_RULE}. Rename or remove this.",
                )
            )
            continue
        doc = files.document(relative, problems)
        if doc is not None:
            deltas[domain] = parse_delta(domain, doc)
            problems.extend(deltas[domain].problems)
    return deltas


def _check_against_config(change: Change, config: Config | None, problems: list[Problem]) -> None:
    """Rules that span files: the short path's limits, and repos in an atlas."""
    proposal, tasks = change.proposal, change.tasks
    default = config.default_review if config else ReviewLevel.SELF
    if proposal and proposal.no_spec_changes and change.deltas:
        problems.append(
            Problem(
                proposal.doc.path,
                WHOLE_FILE,
                "impact-mismatch",
                'The impact says "No spec changes", but the change has deltas. '
                "List the specs it touches, or remove the deltas.",
            )
        )
    if change.short_path and change.design is not None:
        problems.append(
            Problem(
                change.design.doc.path,
                WHOLE_FILE,
                "short-path-design",
                f"A change on the short path has no design. Remove {DESIGN_FILE}, or remove "
                f'the "{PATH}: {SHORT}" line from the proposal.',
            )
        )
    if (
        proposal is not None
        and change.short_path
        and change.review_level(default) is ReviewLevel.INDEPENDENT
    ):
        problems.append(
            Problem(
                proposal.doc.path,
                WHOLE_FILE,
                "short-path-review",
                "A change on the short path is reviewed at self or none, not independently. "
                f'Remove the "{PATH}: {SHORT}" line, or set "{REVIEW}: self" or '
                f'"{REVIEW}: none".',
            )
        )
    for item in tasks.items if tasks else ():
        if item.level_tag is not None:
            problems.append(
                Problem(
                    tasks.doc.path if tasks else change.path,
                    item.index + 1,
                    "obsolete-review-tag",
                    f"Item {item.number} has a review: tag, but a change is reviewed as a "
                    f'whole now. Remove the tag, and set the level with a "{REVIEW}: <level>" '
                    "line in the proposal.",
                )
            )
    if config is None:
        return
    atlas = config.layout is Layout.ATLAS
    known = ", ".join(sorted(config.repo_names)) or "none yet"
    for item in tasks.items if tasks else ():
        if atlas and item.repo is None:
            problems.append(
                Problem(
                    tasks.doc.path if tasks else change.path,
                    item.index + 1,
                    "item-without-repo",
                    f"In an atlas every item names the repo it works in. Add a "
                    f'"Repo: <name>" line under item {item.number} (repos: {known}).',
                )
            )
        elif item.repo is not None and item.repo not in config.repo_names:
            problems.append(
                Problem(
                    tasks.doc.path if tasks else change.path,
                    item.index + 1,
                    "unknown-repo",
                    f'Item {item.number} names the repo "{item.repo}", which the settings '
                    f"don't list (repos: {known}). Fix the name, or add the repo to the settings."
                    if atlas
                    else f'Item {item.number} has a "Repo:" line, but this project is not an '
                    "atlas. Remove the line.",
                )
            )
    for delta in change.deltas.values():
        for repo in delta.repos or ():
            if repo not in config.repo_names:
                problems.append(
                    Problem(
                        delta.doc.path,
                        WHOLE_FILE,
                        "unknown-repo",
                        f'The delta names the repo "{repo}", which the settings don\'t list '
                        f"(repos: {known}). Fix the name, or add the repo to the settings."
                        if atlas
                        else 'The delta has a "Repos:" line, but this project is not an atlas. '
                        "Remove the line.",
                    )
                )


def load_change(
    files: RecordFiles,
    path: str,
    name: str,
    config: Config | None,
    archived_on: datetime.date | None = None,
) -> Change:
    """Read a change folder."""
    problems: list[Problem] = []
    proposal: Proposal | None = None
    design: Design | None = None
    tasks: Tasks | None = None
    tasks_doc: Document | None = None
    deltas: dict[str, Delta] = {}
    for entry in files.entries(path):
        relative = f"{path}/{entry.name}"
        if entry.is_dir and entry.name == SPECS_DIR:
            deltas = _load_deltas(files, path, problems)
        elif entry.is_dir or entry.name not in (PROPOSAL_FILE, DESIGN_FILE, TASKS_FILE):
            problems.append(
                Problem(
                    relative,
                    WHOLE_FILE,
                    "unexpected-file",
                    f"A change holds {PROPOSAL_FILE}, {DESIGN_FILE}, {TASKS_FILE} and a "
                    f"{SPECS_DIR} folder. Move this elsewhere or remove it.",
                )
            )
        else:
            doc = files.document(relative, problems)
            if doc is None:
                continue
            if entry.name == PROPOSAL_FILE:
                proposal = parse_proposal(doc)
                problems.extend(proposal.problems)
            elif entry.name == DESIGN_FILE:
                design = parse_design(doc)
                problems.extend(design.problems)
            else:
                tasks_doc = doc
    version = _format_of(config, archived_on, tasks_doc)
    if tasks_doc is not None:
        tasks = parse_tasks(tasks_doc, version)
        problems.extend(tasks.problems)
    if archived_on is None and proposal is not None and version >= LATEST_FORMAT:
        _old_proposal_lines(proposal, problems)
    change = Change(name, path, archived_on, proposal, deltas, design, tasks, (), version)
    if archived_on is None:
        _check_against_config(change, config, problems)
    return Change(
        name, path, archived_on, proposal, deltas, design, tasks, tuple(sorted(problems)), version
    )


def _format_of(
    config: Config | None, archived_on: datetime.date | None, tasks_doc: Document | None
) -> int:
    """The record format a change is read in.

    An active change follows the record's format. An archived change keeps the
    format it was archived in: from format 2 on, every accepted change has a
    Log section in its task list, which format 1 never wrote.
    """
    if archived_on is not None:
        has_log = tasks_doc is not None and any(
            section.title.strip().casefold() == LOG_SECTION.casefold()
            for section in tasks_doc.sections(2)
        )
        return LATEST_FORMAT if has_log else 1
    if config is None:
        return 1
    return min(config.record_format, LATEST_FORMAT)


def _old_proposal_lines(proposal: Proposal, problems: list[Problem]) -> None:
    """In the latest format a proposal holds no records; report old acceptance and sync lines."""
    for index, line in enumerate(proposal.doc.lines):
        if line.in_fence:
            continue
        if line.text.startswith((f"{ACCEPTED}:", f"{SYNCED}:", "Review override:")):
            problems.append(
                Problem(
                    proposal.doc.path,
                    index + 1,
                    "old-record-format",
                    'This line is in the old record format. Run "wm update" to migrate the '
                    "record; wm keeps the acceptance, the sync and the override as records in "
                    "the task list's Log section.",
                )
            )

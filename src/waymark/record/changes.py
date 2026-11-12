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
from waymark.record.proposal import PATH, SHORT, Proposal, parse_proposal
from waymark.record.tasks import Tasks, parse_tasks
from waymark.record.terms import Layout, ReviewLevel

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

    @property
    def short_path(self) -> bool:
        return self.proposal is not None and self.proposal.short_path

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
    if change.short_path and tasks is not None:
        problems.extend(
            Problem(
                tasks.doc.path,
                item.index + 1,
                "short-path-review",
                f"Item {item.number} needs an independent review, which the short path "
                f'doesn\'t allow. Remove the "{PATH}: {SHORT}" line from the proposal, or '
                "lower the item's review level.",
            )
            for item in tasks.items
            if item.level(default) is ReviewLevel.INDEPENDENT
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
                tasks = parse_tasks(doc)
                problems.extend(tasks.problems)
    change = Change(name, path, archived_on, proposal, deltas, design, tasks, ())
    if archived_on is None:
        _check_against_config(change, config, problems)
    return Change(name, path, archived_on, proposal, deltas, design, tasks, tuple(sorted(problems)))

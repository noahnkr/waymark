"""Changes: one folder per unit of work, holding its proposal, deltas, design and tasks."""

import datetime
from collections.abc import Mapping
from dataclasses import dataclass

from waymark.record.artifacts.config import Config
from waymark.record.artifacts.deltas import Delta, parse_delta
from waymark.record.artifacts.design import (
    DECIDED_BY,
    DECIDERS,
    NO_QUESTIONS,
    OPEN_QUESTIONS,
    STATUS,
    STATUSES,
    Design,
    parse_design,
)
from waymark.record.artifacts.proposal import (
    IMPACT,
    IMPACT_LINES,
    NONE,
    PATH,
    REVIEW,
    SHORT,
    SPECS,
    Acceptance,
    Proposal,
    parse_proposal,
)
from waymark.record.artifacts.tasks import DELEGATE, PLANNER, Tasks, parse_tasks
from waymark.record.evidence.records import RecordKind
from waymark.record.machine.files import RecordFiles
from waymark.record.markdown import labels
from waymark.record.markdown.labels import label_line
from waymark.record.markdown.problems import WHOLE_FILE, Problem
from waymark.record.names import NAME_RULE, is_valid_name
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
    def acceptance(self) -> Acceptance | None:
        """The acceptance that counts: the latest ``(accepted)`` record in the Log.

        A ``(synced)`` record after it carries the fingerprint stamped again for
        the merged specs.
        """
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


def _check_items(tasks: Tasks, problems: list[Problem]) -> None:
    """Every item says who builds it and how it is done, in its lines' order."""
    for item in tasks.items:
        missing = [
            label
            for label, there in (
                (labels.BUILD, item.has_build_line),
                (labels.CRITERIA, item.criteria is not None),
                (labels.VERIFY, item.verify is not None),
            )
            if not there
        ]
        if missing:
            lines = " and ".join(f'a "{label_line(label)}" line' for label in missing)
            message = (
                f"Item {item.number} says who builds it and how it is done: add {lines} under it."
            )
            if labels.BUILD in missing:
                message += (
                    f' The Build line is "{label_line(labels.BUILD, PLANNER)}" or '
                    f'"{label_line(labels.BUILD, DELEGATE)}".'
                )
            problems.append(Problem(tasks.doc.path, item.index + 1, "item-incomplete", message))
        if not _in_order(item.line_order):
            order = ", ".join(labels.ITEM_ORDER)
            problems.append(
                Problem(
                    tasks.doc.path,
                    item.index + 1,
                    "item-order",
                    f"The lines under item {item.number} come in the order {order}, before any "
                    'record. Reorder them, or run "wm check --fix".',
                )
            )


def _in_order(order: tuple[str, ...]) -> bool:
    """Whether an item's label lines follow the item order and come before its records."""
    ranks = [
        labels.ITEM_ORDER.index(line) if line in labels.ITEM_ORDER else len(labels.ITEM_ORDER)
        for line in order
    ]
    return ranks == sorted(ranks)


def _check_decisions(design: Design, problems: list[Problem]) -> None:
    """Each decision weighs options, says whether it is settled and who made it; open questions
    are listed."""
    for decision in design.decisions:
        options = label_line(labels.OPTIONS)
        if decision.options_text:
            line = decision.options_index if decision.options_index is not None else decision.index
            problems.append(
                Problem(
                    design.doc.path,
                    line + 1,
                    "decision-options",
                    f'Decision "{decision.name}" has text on its "{options}" line. Write one '
                    "option per bullet under the line, at least two, and leave the line itself "
                    "empty.",
                )
            )
        elif len(decision.options) < 2:  # noqa: PLR2004 - a decision weighs at least two options
            problems.append(
                Problem(
                    design.doc.path,
                    decision.index + 1,
                    "decision-options",
                    f'Decision "{decision.name}" weighs at least two options. List them under '
                    f'"{options}", one option per bullet.',
                )
            )
        for label, value, allowed in (
            (STATUS, decision.status, STATUSES),
            (DECIDED_BY, decision.decided_by, DECIDERS),
        ):
            if value in allowed:
                continue
            choices = " or ".join(f'"{label_line(label, choice)}"' for choice in allowed)
            found = f'"{value}" is not one of them' if value else "the line is missing"
            problems.append(
                Problem(
                    design.doc.path,
                    decision.index + 1,
                    "decision-format",
                    f'Decision "{decision.name}" has a {choices} line; {found}.',
                )
            )
    if design.open_questions is None:
        problems.append(
            Problem(
                design.doc.path,
                WHOLE_FILE,
                "missing-section",
                f'Add a "## {OPEN_QUESTIONS}" section: a list of the questions still open, '
                f'or "{NO_QUESTIONS}".',
            )
        )
    problems.extend(
        Problem(
            design.doc.path,
            index + 1,
            "open-questions-format",
            f'Open questions are a list, one question per line, or "{NO_QUESTIONS}".',
        )
        for index in design.open_questions_prose
    )


def _check_impact(change: Change, proposal: Proposal, problems: list[Problem]) -> None:
    """The Impact has its three lines, and ``Specs:`` names exactly the specs with a delta.

    A spec named without a delta is reported on the specs folder, so the next step is
    to draft that delta; a delta whose spec isn't named is reported on the proposal.
    """
    if IMPACT not in proposal.sections or not proposal.sections[IMPACT]:
        return  # An empty Impact is already reported as an empty section.
    missing = [label for label in IMPACT_LINES if label not in proposal.impact]
    if missing:
        wanted = ", ".join(f'"{label_line(label)}"' for label in missing)
        problems.append(
            Problem(
                proposal.doc.path,
                WHOLE_FILE,
                "impact-format",
                f"The Impact holds a {wanted} line. Under Specs, name each spec with a delta "
                f'in backticks, or write "{label_line(SPECS, NONE)}".',
            )
        )
    if proposal.impact_specs is None:
        if SPECS in proposal.impact:
            problems.append(
                Problem(
                    proposal.doc.path,
                    WHOLE_FILE,
                    "impact-format",
                    f'The Impact\'s "{label_line(SPECS)}" line names each spec with a delta in '
                    f'backticks, such as "{label_line(SPECS, "`search`")}", or says '
                    f'"{label_line(SPECS, NONE)}".',
                )
            )
        return
    named = set(proposal.impact_specs)
    for domain in sorted(set(change.deltas) - named):
        problems.append(
            Problem(
                proposal.doc.path,
                WHOLE_FILE,
                "impact-mismatch",
                f"The change has a delta for `{domain}`, but the Impact's "
                f'"{label_line(SPECS)}" line doesn\'t name it. Add it there, or remove the delta.',
            )
        )
    for domain in sorted(named - set(change.deltas), key=proposal.impact_specs.index):
        problems.append(
            Problem(
                f"{change.path}/{SPECS_DIR}",
                WHOLE_FILE,
                "impact-mismatch",
                f'The Impact\'s "{label_line(SPECS)}" line names `{domain}`, '
                f"but the change has no delta for it. Draft {SPECS_DIR}/{domain}.md, "
                "or take it off the line.",
            )
        )


def _check_labels(change: Change, problems: list[Problem]) -> None:
    """Every label in the change's files is written bold, the colon inside."""
    parts = (change.proposal, change.design, change.tasks)
    docs = [
        *(part.doc for part in parts if part is not None),
        *(delta.doc for delta in change.deltas.values()),
    ]
    for doc in docs:
        problems.extend(labels.plain_label_problems(doc))


def _check_against_config(change: Change, config: Config | None, problems: list[Problem]) -> None:
    """Rules that span files: the short path's limits, and repos in an atlas."""
    proposal, tasks = change.proposal, change.tasks
    default = config.default_review if config else ReviewLevel.SELF
    _check_labels(change, problems)
    if proposal is not None:
        _check_impact(change, proposal, problems)
    if tasks is not None:
        _check_items(tasks, problems)
    if change.design is not None:
        _check_decisions(change.design, problems)
    if change.short_path and change.design is not None:
        problems.append(
            Problem(
                change.design.doc.path,
                WHOLE_FILE,
                "short-path-design",
                f"A change on the short path has no design. Remove {DESIGN_FILE}, or remove "
                f'the "{label_line(PATH, SHORT)}" line from the proposal.',
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
                f'Remove the "{label_line(PATH, SHORT)}" line, or set '
                f'"{label_line(REVIEW, "self")}" or "{label_line(REVIEW, "none")}".',
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
                    f'"{label_line(labels.REPO, "<name>")}" line under item {item.number} '
                    f"(repos: {known}).",
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
                    else f'Item {item.number} has a "{label_line(labels.REPO)}" line, but this '
                    "project is not an "
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
                        else f'The delta has a "{label_line(labels.REPOS, bullet=False)}" '
                        "line, but this project is not an atlas. Remove the line.",
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

"""Builders for the temporary projects the tests run against.

Nothing here is a sample project: every record is written into a temporary
folder while a test runs.
"""

import datetime
from pathlib import Path

from waymark.record.fingerprint import change_fingerprint
from waymark.record.project import RECORD_DIR, find_project
from waymark.record.proposal import format_acceptance
from waymark.record.record import Record, load_record
from waymark.record.state import ChangeState, RecordState, derive_state
from waymark.record.text import Document

CONFIG = 'wm_version = "0.1.0"\ndefault_review = "self"\nagent_tools = ["some-tool"]\n'
ATLAS_CONFIG = (
    CONFIG
    + '\n[atlas]\nname = "suite"\n\n[atlas.repos.api]\npath = "../suite-api"\n\n[atlas.repos.web]\n'
)

CHARTER = """# Suite

## Vision

Fast search for everyone.

## Goals

- Answers in one step.

## Non-goals

- Ranking by popularity.

## Constraints

- Runs offline.

## Glossary

- Match: a document that satisfies the query.

## Context

The search index is rebuilt nightly.

## Rules

### apply

Run the tests before reporting.

### review

Check every scenario.
"""

DESIGN = """# Design

## Context

Queries can match thousands of documents.

## Approach

Cut the result list after sorting.

## Decisions

### Decision: Where to cut

- Options: in the query, or after sorting
- Choice: after sorting
- Why: the order must be final first

## Risks and trade-offs

Sorting everything costs memory.
"""

TASKS = """# Tasks

## 1. Limit

- [ ] 1.1 Cap the result count
  - Criteria: at most fifty results come back
  - Verify: a test covers fifty-one matches
- [ ] 1.2 Document the limit   `review: none`
"""


def document(text: str, path: str = "file.md") -> Document:
    return Document.parse(path, text)


def requirement(
    name: str = "Result limit",
    statement: str = "A search SHALL return at most fifty results.",
    scenario: str = "Many matches",
) -> str:
    return (
        f"### Requirement: {name}\n"
        f"{statement}\n"
        "\n"
        f"#### Scenario: {scenario}\n"
        "- GIVEN an index with many matches\n"
        "- WHEN a search runs\n"
        "- THEN the limit holds\n"
    )


def spec(*requirements: str, title: str = "Search", purpose: str = "How search behaves.") -> str:
    blocks = requirements or (requirement(),)
    return f"# {title}\n\n## Purpose\n\n{purpose}\n\n## Requirements\n\n" + "\n".join(blocks)


def delta(
    *,
    title: str = "Search",
    added: tuple[str, ...] = (),
    modified: tuple[str, ...] = (),
    removed: tuple[tuple[str, str], ...] = (),
    purpose: str | None = None,
    repos: str | None = None,
) -> str:
    parts = [f"# {title}\n"]
    if repos is not None:
        parts.append(f"Repos: {repos}\n")
    if purpose is not None:
        parts.append(f"## Purpose\n\n{purpose}\n")
    if added:
        parts.append("## Added requirements\n\n" + "\n".join(added))
    if modified:
        parts.append("## Modified requirements\n\n" + "\n".join(modified))
    if removed:
        blocks = [f"### Requirement: {name}\nReason: {reason}\n" for name, reason in removed]
        parts.append("## Removed requirements\n\n" + "\n".join(blocks))
    return "\n".join(parts)


def proposal(
    *,
    owner: str = "Sam Doe",
    short: bool = False,
    impact: str = "Specs: search.",
    outcome: str | None = None,
) -> str:
    facts = f"Owner: {owner}\n" + ("Path: short\n" if short else "")
    text = (
        f"# Limit the results\n\n{facts}\n"
        "## Why\n\nLong result lists are slow.\n\n"
        "## What changes\n\nSearch returns a capped list.\n\n"
        "## Non-goals\n\nPaging.\n\n"
        f"## Impact\n\n{impact}\n"
    )
    if outcome is not None:
        text += f"\n## Outcome\n\n{outcome}\n"
    return text


class Workspace:
    """A temporary project: a folder with a record in it."""

    def __init__(self, root: Path, config: str = CONFIG) -> None:
        self.root = root
        self.write("config.toml", config)
        self.write("charter.md", CHARTER)

    def path(self, relative: str) -> Path:
        return self.root / RECORD_DIR / relative

    def write(self, relative: str, text: str) -> Path:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        return target

    def read(self, relative: str) -> str:
        return self.path(relative).read_bytes().decode("utf-8")

    def replace(self, relative: str, old: str, new: str) -> None:
        text = self.read(relative)
        assert text.count(old) == 1, f"{old!r} is not in {relative} exactly once"
        self.write(relative, text.replace(old, new))

    def change(
        self,
        name: str = "add-limit",
        *,
        proposal_text: str | None = None,
        deltas: dict[str, str] | None = None,
        design: str | None = DESIGN,
        tasks: str | None = TASKS,
    ) -> str:
        """Write a whole change; by default one that adds a requirement to a new spec."""
        folder = f"changes/{name}"
        self.write(f"{folder}/proposal.md", proposal_text or proposal())
        if deltas is None:
            deltas = {"search": delta(added=(requirement(),), purpose="How search behaves.")}
        for domain, text in deltas.items():
            self.write(f"{folder}/specs/{domain}.md", text)
        if design is not None:
            self.write(f"{folder}/design.md", design)
        if tasks is not None:
            self.write(f"{folder}/tasks.md", tasks)
        return folder

    def record(self) -> Record:
        return load_record(find_project(self.root))

    def state(self) -> RecordState:
        return derive_state(self.record())

    def change_state(self, name: str = "add-limit") -> ChangeState:
        return self.state().changes[name]

    def accept(self, name: str = "add-limit") -> None:
        """Write the acceptance line the way the accept command will."""
        record = self.record()
        fingerprint = change_fingerprint(record.changes[name], record.specs, record.default_review)
        line = format_acceptance(datetime.date(2026, 1, 15), "Sam Doe", fingerprint)
        relative = f"changes/{name}/proposal.md"
        lines = [
            line_ for line_ in self.read(relative).split("\n") if not line_.startswith("Accepted:")
        ]
        owner = next(index for index, text in enumerate(lines) if text.startswith("Owner:"))
        lines.insert(owner + 1, line)
        self.write(relative, "\n".join(lines))

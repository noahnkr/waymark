"""The fixed vocabulary of the record: levels, verdicts, steps and phases."""

from enum import StrEnum


class Layout(StrEnum):
    """Where the record lives."""

    REPO = "repo"
    ATLAS = "atlas"


class ReviewLevel(StrEnum):
    """How a task item is checked."""

    SELF = "self"
    INDEPENDENT = "independent"
    NONE = "none"


class Verdict(StrEnum):
    """What a reviewer concluded about a task item."""

    PASS = "pass"
    CHANGES = "changes"
    SPEC_GAP = "spec-gap"


class Step(StrEnum):
    """A workflow step an agent works in; the charter holds rules for each."""

    EXPLORE = "explore"
    PROPOSE = "propose"
    SPECS = "specs"
    DESIGN = "design"
    TASKS = "tasks"
    APPLY = "apply"
    REVIEW = "review"
    ARCHIVE = "archive"


class Phase(StrEnum):
    """How far an active change has come."""

    PROPOSED = "proposed"
    SPECIFIED = "specified"
    DESIGNED = "designed"
    PLANNED = "planned"
    ACCEPTED = "accepted"
    APPLYING = "applying"
    APPLIED = "applied"

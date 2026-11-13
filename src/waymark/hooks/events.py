"""The neutral events an agent tool reports, and the decisions it gets back."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Role(StrEnum):
    """Who is acting: the main session, or one of the two delegated agents."""

    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"


class EventKind(StrEnum):
    """The moments wm is asked about."""

    SESSION_START = "session-start"
    DELEGATE = "delegate"
    EDIT = "edit"
    EDITED = "edited"
    COMMAND = "command"
    AGENT_STOP = "agent-stop"


@dataclass(frozen=True)
class Replacement:
    """One text replacement an edit makes in a file."""

    old: str
    new: str
    everywhere: bool = False


@dataclass(frozen=True)
class Event:
    """One thing an agent is about to do, or has just done.

    Only the fields that belong to the event's kind are set:

    - ``DELEGATE``: ``agent`` (the agent being started) and ``prompt``;
    - ``EDIT``: ``path``, and either the file's whole new ``content`` or the
      ``replacements`` the edit makes;
    - ``EDITED``: ``path``;
    - ``COMMAND``: ``command``;
    - ``AGENT_STOP``: ``message`` (the agent's final words) and ``retried``
      (it was already asked once to fix its ending).
    """

    kind: EventKind
    cwd: Path
    role: Role = Role.PLANNER
    agent: str = ""
    prompt: str = ""
    path: Path | None = None
    content: str | None = None
    replacements: tuple[Replacement, ...] = ()
    command: str = ""
    message: str = ""
    retried: bool = False


@dataclass(frozen=True)
class Decision:
    """The answer to an event.

    ``allow`` false refuses the action, with ``reason`` saying what is wrong
    and what to do. ``context`` is text for the agent to read. ``notice`` is
    text for the human.
    """

    allow: bool = True
    reason: str = ""
    context: str = ""
    notice: str = ""


ALLOW = Decision()

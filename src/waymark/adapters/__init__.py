"""Adapters: one per agent tool.

An adapter renders the files its tool needs and translates the tool's hook
events to and from wm's neutral ones. It holds no rules: every decision is
made by the core, so it is the same in every tool.
"""

import datetime
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Capabilities:
    """What an agent tool offers. The workflow adapts to what is missing."""

    skills: bool
    subagents: bool
    hooks: bool


@dataclass(frozen=True)
class HookReply:
    """What a hook command prints and exits with, in the tool's own protocol."""

    stdout: str = ""
    stderr: str = ""
    code: int = 0


class Adapter(ABC):
    """An agent tool's adapter.

    ``reads`` names the project files the adapter merges its settings into;
    their current text is handed to ``files``. Paths are relative to the
    project's top folder, with forward slashes.
    """

    name: str
    title: str
    capabilities: Capabilities
    reads: tuple[str, ...] = ()

    @abstractmethod
    def files(self, existing: Mapping[str, str | None]) -> dict[str, str]:
        """The files Waymark owns for this tool, with their full text."""

    def hook(
        self, event: str, payload: Mapping[str, Any], cwd: Path, today: datetime.date
    ) -> HookReply:
        """Answer one of the tool's hook events. A tool without hooks answers nothing."""
        del event, payload, cwd, today
        return HookReply()


class UnknownToolError(Exception):
    """No adapter has this name."""


_REGISTRY: dict[str, Adapter] = {}


def register(adapter: Adapter) -> None:
    """Add an adapter. Adding a tool needs nothing else from the core."""
    _REGISTRY[adapter.name] = adapter


def names() -> tuple[str, ...]:
    """Every registered adapter's name."""
    return tuple(sorted(_REGISTRY))


def get(name: str) -> Adapter:
    """The adapter for a tool."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownToolError(name) from None


def _register_built_in() -> None:
    from waymark.adapters.claude_code import ClaudeCodeAdapter  # noqa: PLC0415

    register(ClaudeCodeAdapter())


_register_built_in()

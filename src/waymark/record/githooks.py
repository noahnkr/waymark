"""The committed git hooks: where they live, what they are, and whether git uses them.

The hooks sit in ``.waymark/hooks/`` and every clone points git at them with
``core.hooksPath``. A repository that already uses another hook manager is
left alone.
"""

import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waymark.record import git, templates

HOOKS_DIR = ".waymark/hooks"
HOOKS = {"commit-msg": "hook-commit-msg", "pre-commit": "hook-pre-commit"}
"""Each hook's file name, and its template."""

_MANAGER_FILES = (
    ".husky",
    ".pre-commit-config.yaml",
    "lefthook.yml",
    "lefthook.yaml",
    "lefthook.json",
    ".lefthook.yml",
    ".lefthook.yaml",
    ".overcommit.yml",
)


class HooksState(StrEnum):
    """Whether this clone runs the committed hooks."""

    SET = "set"
    NOT_SET = "not-set"
    ABSENT = "absent"
    MANAGED = "managed"


@dataclass(frozen=True)
class HooksStatus:
    """Whether this clone runs the hooks; ``manager`` names another hook setup, if any."""

    state: HooksState
    manager: str | None = None


ATTRIBUTES = f"{HOOKS_DIR}/.gitattributes"
_ATTRIBUTES_TEXT = (
    "# Written by wm (Waymark): the hooks are shell scripts, which need LF line endings\n"
    "# on every platform, whatever git's line-ending settings say.\n"
    "* text eol=lf\n"
)


def hook_scripts() -> dict[str, str]:
    """Each committed hook script's path, relative to the repository's top, with its text."""
    return {f"{HOOKS_DIR}/{name}": templates.render(source) for name, source in HOOKS.items()}


def hook_files() -> dict[str, str]:
    """Every file in the hooks folder: the scripts, and the attributes that keep them LF."""
    return {**hook_scripts(), ATTRIBUTES: _ATTRIBUTES_TEXT}


def hook_manager(root: Path) -> str | None:
    """Another hook setup this repository already uses, in a few words; None when there is none."""
    configured = git.config_value(root, "core.hooksPath")
    if configured is not None and Path(configured).as_posix().rstrip("/") != HOOKS_DIR:
        return f'core.hooksPath is set to "{configured}"'
    for name in _MANAGER_FILES:
        if (root / name).exists():
            return f"the repository has {name}"
    try:
        folder = git.default_hooks_folder(root)
    except git.GitError:
        return None
    for name in HOOKS:
        if (folder / name).is_file():
            return f"git already runs its own {name} hook"
    return None


def hooks_status(root: Path) -> HooksStatus:
    """Whether this clone runs the committed hooks."""
    manager = hook_manager(root)
    if manager is not None:
        return HooksStatus(HooksState.MANAGED, manager)
    if not all((root / path).is_file() for path in hook_scripts()):
        return HooksStatus(HooksState.ABSENT)
    configured = git.config_value(root, "core.hooksPath")
    if configured is not None and Path(configured).as_posix().rstrip("/") == HOOKS_DIR:
        return HooksStatus(HooksState.SET)
    return HooksStatus(HooksState.NOT_SET)


def make_executable(root: Path) -> None:
    """Give the hook files their executable bit, which git needs to run them on Linux and macOS."""
    for relative in hook_scripts():
        path = root / relative
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def read_message(path: Path) -> str:
    """A commit message file, as git wrote it."""
    return path.read_bytes().decode("utf-8", errors="replace")

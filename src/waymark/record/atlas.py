"""Finding an atlas and its code repos on this machine.

The registry is asked first. When it has no usable entry, a relative-path
hint is tried, and used only when it leads to the right repository: an atlas
whose settings carry the expected name, or a git repository's top folder whose
pointer file, if it has one, names the expected atlas.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from waymark.record import git
from waymark.record.config import CONFIG_FILE, RECORD_DIR, CodeRepo, parse_config
from waymark.record.pointer import POINTER_FILE, Pointer, parse_pointer
from waymark.record.registry import Registry

REGISTER = "wm atlas register"


class Found(StrEnum):
    """How a folder was found."""

    REGISTRY = "registry"
    HINT = "hint"
    MISSING = "missing"


@dataclass(frozen=True)
class Location:
    """Where an atlas or code repo is on this machine, if anywhere.

    ``detail`` says why it is missing, or, when only its hint found it, how to
    register it. It names no folder, so it can go into JSON as it is.
    """

    name: str
    folder: Path | None
    found: Found
    detail: str = ""


def _read(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def atlas_name_at(folder: Path) -> str | None:
    """The name of the atlas whose top folder this is; None when it isn't one."""
    text = _read(folder / RECORD_DIR / CONFIG_FILE)
    config = parse_config(text)[0] if text is not None else None
    return config.atlas_name if config else None


def read_pointer(folder: Path) -> tuple[Pointer | None, str | None]:
    """A folder's pointer file, and why it can't be read, if it can't; (None, None) without one."""
    text = _read(folder / POINTER_FILE)
    if text is None:
        return None, None
    return parse_pointer(text)


def pointer_atlas(folder: Path) -> tuple[str | None, str | None]:
    """The atlas a folder's pointer file names, and why it can't be read, if it can't."""
    pointer, problem = read_pointer(folder)
    return (pointer.atlas if pointer else None), problem


def is_repo_top(folder: Path) -> bool:
    """Whether a folder is the top folder of a git repository."""
    if not folder.is_dir():
        return False
    top = git.repository_root(folder)
    return top is not None and top.resolve() == folder.resolve()


def repo_problem(folder: Path, atlas: str) -> str | None:
    """Why a folder can't be the code repo of an atlas; None when it can. Names no folder."""
    if not folder.is_dir():
        return "the folder doesn't exist"
    if not is_repo_top(folder):
        return "the folder is not the top folder of a git repository"
    named, _ = pointer_atlas(folder)
    if named is not None and named != atlas:
        return f'its pointer names the atlas "{named}", not "{atlas}"'
    return None


def _hinted(base: Path, hint: str | None) -> Path | None:
    if not hint:
        return None
    return (base / hint).resolve()


def locate_atlas(
    name: str, registry: Registry, base: Path | None = None, hint: str | None = None
) -> Location:
    """Find an atlas: through the registry, or through a hint relative to ``base``."""
    entry = registry.atlas(name)
    stale = ""
    if entry is not None and entry.path is not None:
        if atlas_name_at(entry.path) == name:
            return Location(name, entry.path, Found.REGISTRY)
        stale = " The registry's entry points to a folder that holds no atlas of that name."
    folder = _hinted(base, hint) if base is not None else None
    if folder is not None and atlas_name_at(folder) == name:
        detail = (
            f'Found the atlas "{name}" through its path hint. '
            f'To register it on this machine, run "{REGISTER}" there.'
        )
        return Location(name, folder, Found.HINT, detail)
    tried = f" Its path hint ({hint}) doesn't lead to it." if hint else ""
    return Location(
        name,
        None,
        Found.MISSING,
        f'The atlas "{name}" is not on this machine\'s registry.{stale}{tried} '
        f'Clone it, then run "{REGISTER}" in it.',
    )


def locate_repo(atlas: str, atlas_root: Path, repo: CodeRepo, registry: Registry) -> Location:
    """Find one of an atlas's code repos: through the registry, or its hint."""
    registered = registry.repo(atlas, repo.name)
    stale = ""
    if registered is not None:
        problem = repo_problem(registered, atlas)
        if problem is None:
            return Location(repo.name, registered, Found.REGISTRY)
        stale = f" The registry's entry is unusable: {problem}."
    folder = _hinted(atlas_root, repo.path_hint)
    if folder is not None and repo_problem(folder, atlas) is None:
        detail = (
            f'Found the code repo "{repo.name}" through its path hint. '
            f'To register it on this machine, run "{REGISTER}" in the atlas.'
        )
        return Location(repo.name, folder, Found.HINT, detail)
    tried = f" Its path hint ({repo.path_hint}) doesn't lead to it." if repo.path_hint else ""
    return Location(
        repo.name,
        None,
        Found.MISSING,
        f'The code repo "{repo.name}" is not on this machine\'s registry.{stale}{tried} '
        f'Register its folder with "{REGISTER} {repo.name} <folder>".',
    )


def contains(folder: Path, path: Path) -> bool:
    """Whether a path is a folder or inside it."""
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return False
    return True

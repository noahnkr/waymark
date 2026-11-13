"""Finding the project: the folder that holds the record.

From inside the repository or atlas that holds the record, it is found by
looking upward for the record's settings. From inside a code repo that an
atlas covers, it is found through the code repo's pointer file, or through
this machine's registry.
"""

from dataclasses import dataclass
from pathlib import Path

from waymark.record.atlas import Found, contains, locate_atlas
from waymark.record.config import CONFIG_FILE, RECORD_DIR
from waymark.record.pointer import POINTER_FILE, parse_pointer
from waymark.record.registry import Registry, load_registry

__all__ = ["RECORD_DIR", "Project", "ProjectNotFoundError", "find_project"]


class ProjectNotFoundError(Exception):
    """No record was found at or above the starting folder, nor through a code repo."""

    def __init__(self, start: Path, reason: str | None = None) -> None:
        super().__init__(
            reason
            or (
                f'No Waymark project found at or above "{start}". '
                f'A project has a "{RECORD_DIR}/{CONFIG_FILE}" file at its top. '
                "Change to the project's folder, or initialize one."
            )
        )
        self.start = start


@dataclass(frozen=True)
class Project:
    """A project: the repository, or the atlas, whose top folder holds the record.

    When it was found from inside one of an atlas's code repos, ``code_repo``
    is that repo's top folder. ``notes`` are things worth telling the person
    running the command, such as a hint that could be registered.
    """

    root: Path
    code_repo: Path | None = None
    notes: tuple[str, ...] = ()

    @property
    def record_root(self) -> Path:
        return self.root / RECORD_DIR


def _upward(start: Path, relative: str) -> Path | None:
    for folder in (start, *start.parents):
        if (folder / relative).is_file():
            return folder
    return None


def _through_pointer(start: Path, folder: Path, registry: Registry) -> Project:
    try:
        text = (folder / POINTER_FILE).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        reason = f"{folder / POINTER_FILE} can't be read ({error})."
        raise ProjectNotFoundError(start, reason) from error
    pointer, problem = parse_pointer(text)
    if pointer is None:
        raise ProjectNotFoundError(start, f"{folder / POINTER_FILE}: {problem}")
    location = locate_atlas(pointer.atlas, registry, folder, pointer.path_hint)
    if location.folder is None:
        raise ProjectNotFoundError(
            start, f'This code repo points to the atlas "{pointer.atlas}". {location.detail}'
        )
    notes = (location.detail,) if location.found is Found.HINT else ()
    return Project(location.folder, folder, notes)


def _through_registry(start: Path, registry: Registry) -> Project | None:
    matches = sorted(
        (entry.name, repo_folder)
        for entry in registry.atlases.values()
        for repo_folder in entry.repos.values()
        if contains(repo_folder, start)
    )
    atlases = sorted({name for name, _ in matches})
    if len(atlases) > 1:
        raise ProjectNotFoundError(
            start,
            f"This folder is a code repo of several atlases ({', '.join(atlases)}). Run wm "
            'from the atlas you mean, or give this repo a pointer with "wm atlas point <atlas>".',
        )
    if not matches:
        return None
    name, repo_folder = matches[0]
    location = locate_atlas(name, registry)
    if location.folder is None:
        raise ProjectNotFoundError(start, location.detail)
    return Project(location.folder, repo_folder)


def find_project(start: Path, registry: Registry | None = None) -> Project:
    """Find the project that contains a folder, or the atlas a code repo belongs to.

    The record sits in the same place in a repository and in an atlas, so both
    are found the same way; the settings say which one it is.
    """
    origin = start.resolve()
    found = _upward(origin, f"{RECORD_DIR}/{CONFIG_FILE}")
    if found is not None:
        return Project(found)
    known = load_registry() if registry is None else registry
    pointed = _upward(origin, POINTER_FILE)
    if pointed is not None:
        return _through_pointer(start, pointed, known)
    project = _through_registry(origin, known)
    if project is None:
        raise ProjectNotFoundError(start)
    return project

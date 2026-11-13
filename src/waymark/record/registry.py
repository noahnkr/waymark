"""The per-machine registry: where each atlas and its code repos sit on this machine.

It lives in the user's settings folder, outside every repository, and is
written whole by wm. ``WAYMARK_REGISTRY`` names another file to use instead.
"""

import json
import os
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath

from waymark.record.files import RecordFiles
from waymark.record.store import Transaction

REGISTRY_ENV = "WAYMARK_REGISTRY"
REGISTRY_FILE = "registry.toml"
_FOLDER = "waymark"

_HEADER = (
    "# The atlases and code repos on this machine, and where each one is.\n"
    '# Written by wm ("wm atlas register"). "wm atlas doctor" checks it.\n'
)


def registry_path(
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    """Where this machine's registry is: the user's settings folder, or ``WAYMARK_REGISTRY``."""
    env = os.environ if environ is None else environ
    override = env.get(REGISTRY_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    where = sys.platform if platform is None else platform
    base = Path.home() if home is None else home
    if where.startswith("win"):
        appdata = env.get("APPDATA", "").strip()
        folder = Path(appdata) if appdata else base / "AppData" / "Roaming"
    elif where == "darwin":
        folder = base / "Library" / "Application Support"
    else:
        xdg = env.get("XDG_CONFIG_HOME", "").strip()
        folder = Path(xdg) if xdg and PurePosixPath(xdg).is_absolute() else base / ".config"
    return folder / _FOLDER / REGISTRY_FILE


@dataclass(frozen=True)
class AtlasEntry:
    """A registered atlas: its folder, and the folders of its code repos."""

    name: str
    path: Path | None
    repos: Mapping[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class Registry:
    """The registry as read from its file. ``problems`` says what could not be read."""

    path: Path
    atlases: Mapping[str, AtlasEntry] = field(default_factory=dict)
    problems: tuple[str, ...] = ()

    def atlas(self, name: str) -> AtlasEntry | None:
        return self.atlases.get(name)

    def repo(self, atlas: str, repo: str) -> Path | None:
        entry = self.atlases.get(atlas)
        return entry.repos.get(repo) if entry else None

    def with_atlas(self, name: str, path: Path) -> "Registry":
        """The registry with an atlas registered at a folder, keeping its repos."""
        current = self.atlases.get(name)
        repos = current.repos if current else {}
        return replace(self, atlases={**self.atlases, name: AtlasEntry(name, path, repos)})

    def with_repo(self, atlas: str, repo: str, path: Path) -> "Registry":
        """The registry with one of an atlas's code repos registered at a folder."""
        current = self.atlases.get(atlas) or AtlasEntry(atlas, None)
        entry = AtlasEntry(atlas, current.path, {**current.repos, repo: path})
        return replace(self, atlases={**self.atlases, atlas: entry})


def _string(value: str) -> str:
    """A TOML basic string. JSON's escapes are all valid in TOML."""
    return json.dumps(value, ensure_ascii=False)


def render_registry(registry: Registry) -> str:
    """The registry's file text."""
    parts = [_HEADER]
    for name in sorted(registry.atlases):
        entry = registry.atlases[name]
        parts.append(f"\n[atlases.{_string(name)}]\n")
        if entry.path is not None:
            parts.append(f"path = {_string(str(entry.path))}\n")
        for repo in sorted(entry.repos):
            parts.append(f"\n[atlases.{_string(name)}.repos.{_string(repo)}]\n")
            parts.append(f"path = {_string(str(entry.repos[repo]))}\n")
    return "".join(parts)


def _folder(table: object) -> Path | None:
    value = table.get("path") if isinstance(table, dict) else None
    return Path(value) if isinstance(value, str) and value.strip() else None


def parse_registry(path: Path, text: str) -> Registry:
    """Read the registry's text. Entries that can't be read are reported and left out."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return Registry(path, problems=(f"The registry is not valid TOML: {error}.",))
    problems: list[str] = []
    atlases: dict[str, AtlasEntry] = {}
    tables = data.get("atlases", {})
    if not isinstance(tables, dict) or set(data) - {"atlases"}:
        return Registry(path, problems=('The registry holds only "[atlases.<name>]" tables.',))
    for name, table in tables.items():
        if not isinstance(table, dict):
            problems.append(f'The entry for the atlas "{name}" is not a table.')
            continue
        repos: dict[str, Path] = {}
        repo_tables = table.get("repos", {})
        for repo, repo_table in repo_tables.items() if isinstance(repo_tables, dict) else ():
            folder = _folder(repo_table)
            if folder is None:
                problems.append(f'The code repo "{repo}" of the atlas "{name}" has no path.')
            else:
                repos[repo] = folder
        atlases[name] = AtlasEntry(name, _folder(table), repos)
    return Registry(path, atlases, tuple(problems))


def load_registry(path: Path | None = None) -> Registry:
    """Read this machine's registry. A registry that doesn't exist yet is empty."""
    where = registry_path() if path is None else path
    try:
        text = where.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return Registry(where)
    except (OSError, UnicodeDecodeError) as error:
        return Registry(where, problems=(f"The registry can't be read ({error}).",))
    return parse_registry(where, text)


def stage_registry(registry: Registry) -> Transaction:
    """A transaction that writes the registry's file; the caller commits it."""
    transaction = Transaction(RecordFiles(registry.path.parent))
    transaction.write(registry.path.name, render_registry(registry))
    return transaction

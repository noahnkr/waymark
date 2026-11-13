"""Settings: ``config.toml`` at the record's root."""

import re
import tomllib
from dataclasses import dataclass
from typing import Any

from waymark.record.problems import WHOLE_FILE, Problem
from waymark.record.terms import Layout, ReviewLevel

CONFIG_FILE = "config.toml"
RECORD_DIR = "waymark"
"""The record's folder, at the top of a repository or an atlas."""

_REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
RECORD_FORMAT = 1
"""The record format this version of wm reads and writes."""

_TOP_KEYS = frozenset(
    {
        "wm_version",
        "record_format",
        "default_review",
        "commit_scopes",
        "agent_tools",
        "atlas",
        "references",
    }
)
_ATLAS_KEYS = frozenset({"name", "repos"})
_REPO_KEYS = frozenset({"path"})
_REFERENCE_KEYS = frozenset({"path"})


@dataclass(frozen=True)
class CodeRepo:
    """A code repository an atlas covers, with an optional relative-path hint."""

    name: str
    path_hint: str | None


@dataclass(frozen=True)
class Reference:
    """Another atlas whose specs this project reads, with an optional relative-path hint."""

    atlas: str
    path_hint: str | None


@dataclass(frozen=True)
class Config:
    """The settings wm reads."""

    wm_version: str
    record_format: int
    default_review: ReviewLevel
    commit_scopes: tuple[str, ...] | None
    agent_tools: tuple[str, ...]
    atlas_name: str | None
    repos: tuple[CodeRepo, ...]
    references: tuple[Reference, ...] = ()

    @property
    def layout(self) -> Layout:
        return Layout.REPO if self.atlas_name is None else Layout.ATLAS

    @property
    def repo_names(self) -> frozenset[str]:
        return frozenset(repo.name for repo in self.repos)


class _Reader:
    """Collects problems while values are pulled out of the parsed TOML."""

    def __init__(self) -> None:
        self.problems: list[Problem] = []

    def problem(self, code: str, message: str) -> None:
        self.problems.append(Problem(CONFIG_FILE, WHOLE_FILE, code, message))

    def unknown_keys(self, table: dict[str, Any], known: frozenset[str], where: str) -> None:
        for key in sorted(set(table) - known):
            self.problem(
                "unknown-setting", f'"{key}" is not a setting{where}. Remove it or fix its name.'
            )

    def string(self, table: dict[str, Any], key: str, where: str = "") -> str | None:
        value = table.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        self.problem("invalid-setting", f'Set "{key}"{where} to a non-empty string.')
        return None

    def strings(self, table: dict[str, Any], key: str) -> tuple[str, ...] | None:
        value = table.get(key)
        if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
            return tuple(value)
        self.problem("invalid-setting", f'Set "{key}" to a list of non-empty strings.')
        return None

    def format_number(self, table: dict[str, Any]) -> int | None:
        value = table.get("record_format")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
            return value
        self.problem(
            "invalid-setting",
            'Set "record_format" to the record\'s format number. It is written by wm; '
            f"a record made by this version has {RECORD_FORMAT}.",
        )
        return None

    def review_level(self, table: dict[str, Any]) -> ReviewLevel | None:
        value = table.get("default_review")
        if isinstance(value, str) and value in set(ReviewLevel):
            return ReviewLevel(value)
        levels = ", ".join(f'"{level.value}"' for level in ReviewLevel)
        self.problem("invalid-setting", f'Set "default_review" to one of {levels}.')
        return None

    def repos(self, atlas: dict[str, Any]) -> tuple[CodeRepo, ...]:
        tables = atlas.get("repos", {})
        if not isinstance(tables, dict):
            self.problem(
                "invalid-setting",
                'Name each code repo with its own "[atlas.repos.<name>]" table.',
            )
            return ()
        repos: list[CodeRepo] = []
        for name, table in tables.items():
            where = f' in "[atlas.repos.{name}]"'
            if not _REPO_NAME.fullmatch(name) or not isinstance(table, dict):
                self.problem(
                    "invalid-setting",
                    f'"{name}" is not a usable repo entry. Use "[atlas.repos.<name>]" with '
                    "letters, digits, dots, hyphens or underscores in the name.",
                )
                continue
            self.unknown_keys(table, _REPO_KEYS, where)
            hint = self.string(table, "path", where) if "path" in table else None
            repos.append(CodeRepo(name, hint))
        return tuple(repos)

    def references(self, tables: object) -> tuple[Reference, ...]:
        if not isinstance(tables, dict):
            self.problem(
                "invalid-setting",
                'Name each referenced atlas with its own "[references.<atlas>]" table.',
            )
            return ()
        references: list[Reference] = []
        for name, table in tables.items():
            where = f' in "[references.{name}]"'
            if not _REPO_NAME.fullmatch(name) or not isinstance(table, dict):
                self.problem(
                    "invalid-setting",
                    f'"{name}" is not a usable reference. Use "[references.<atlas>]" with the '
                    "other atlas's name.",
                )
                continue
            self.unknown_keys(table, _REFERENCE_KEYS, where)
            hint = self.string(table, "path", where) if "path" in table else None
            references.append(Reference(name, hint))
        return tuple(references)


def parse_config(text: str) -> tuple[Config | None, tuple[Problem, ...]]:
    """Read the settings. Returns no config when any setting is unusable."""
    reader = _Reader()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        reader.problem("invalid-toml", f"The file is not valid TOML: {error}. Fix the syntax.")
        return None, tuple(reader.problems)

    reader.unknown_keys(data, _TOP_KEYS, "")
    wm_version = reader.string(data, "wm_version")
    record_format = reader.format_number(data)
    default_review = reader.review_level(data)
    agent_tools = reader.strings(data, "agent_tools")
    commit_scopes = reader.strings(data, "commit_scopes") if "commit_scopes" in data else None

    atlas_name: str | None = None
    repos: tuple[CodeRepo, ...] = ()
    if "atlas" in data:
        atlas = data["atlas"]
        if isinstance(atlas, dict):
            reader.unknown_keys(atlas, _ATLAS_KEYS, ' in "[atlas]"')
            atlas_name = reader.string(atlas, "name", ' in "[atlas]"')
            repos = reader.repos(atlas)
        else:
            reader.problem("invalid-setting", 'Write the atlas settings as an "[atlas]" table.')
    references = reader.references(data["references"]) if "references" in data else ()
    if atlas_name is not None and atlas_name in {reference.atlas for reference in references}:
        reader.problem("invalid-setting", "An atlas can't reference itself. Remove the reference.")

    if (
        reader.problems
        or wm_version is None
        or record_format is None
        or default_review is None
        or agent_tools is None
    ):
        return None, tuple(reader.problems)
    config = Config(
        wm_version,
        record_format,
        default_review,
        commit_scopes,
        agent_tools,
        atlas_name,
        repos,
        references,
    )
    return config, ()

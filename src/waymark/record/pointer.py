"""The pointer a code repo may carry: which atlas holds its record, and where.

It is a pointer-only ``waymark/config.toml`` in the code repo's top folder,
whose only table is ``[pointer]``: the atlas's name, an optional relative-path
hint and the pinned wm version. It holds no record. wm 0.1.1 and earlier wrote
the same settings, at the top level, to ``.waymark/atlas.toml``, which is still
read when the code repo has no ``waymark/config.toml``. A code repo needs no
Waymark files; the pointer is written only when asked for.
"""

import json
import tomllib
from dataclasses import dataclass
from typing import Any

from waymark.record.config import CONFIG_FILE, RECORD_DIR

POINTER_TABLE = "pointer"
POINTER_FILE = f"{RECORD_DIR}/{CONFIG_FILE}"
OLD_POINTER_DIR = ".waymark"
OLD_POINTER_FILE = f"{OLD_POINTER_DIR}/atlas.toml"
_KEYS = frozenset({"atlas", "path", "wm_version"})


@dataclass(frozen=True)
class Pointer:
    """What a code repo's pointer says."""

    atlas: str
    path_hint: str | None
    wm_version: str | None


def _load(text: str) -> dict[str, Any] | None:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None


def is_pointer(text: str) -> bool:
    """Whether a ``waymark/config.toml`` is a pointer rather than a record's settings.

    It is a pointer when it is valid TOML with a ``[pointer]`` table.
    """
    data = _load(text)
    return data is not None and isinstance(data.get(POINTER_TABLE), dict)


def _pointer_table(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """A ``waymark/config.toml`` pointer's ``[pointer]`` table, or why it has none to read."""
    table = data.get(POINTER_TABLE)
    if not isinstance(table, dict):
        return None, f"{POINTER_FILE} has no [{POINTER_TABLE}] table."
    others = sorted(set(data) - {POINTER_TABLE})
    if others:
        return None, (
            f'{POINTER_FILE} holds "{others[0]}" beside its [{POINTER_TABLE}] table, and a '
            "pointer holds nothing else."
        )
    return table, None


def parse_pointer(text: str, *, old: bool = False) -> tuple[Pointer | None, str | None]:
    """Read a pointer. Returns the pointer, or why it can't be read.

    With ``old``, the text is a ``.waymark/atlas.toml``, whose settings are at
    the top level; otherwise it is a ``waymark/config.toml``, whose settings
    are in its ``[pointer]`` table and which holds nothing else.
    """
    name = OLD_POINTER_FILE if old else POINTER_FILE
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return None, f"{name} is not valid TOML: {error}."
    if not old:
        table, problem = _pointer_table(data)
        if table is None:
            return None, problem
        data = table
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        return None, f'{name} holds "{unknown[0]}", which is not one of its settings.'
    values = {key: data.get(key) for key in _KEYS}
    if not all(value is None or isinstance(value, str) for value in values.values()):
        return None, f"{name} holds a setting that is not a string."
    atlas = (values["atlas"] or "").strip()
    if not atlas:
        return None, f'{name} names no atlas. Set "atlas" to the atlas\'s name.'
    hint = (values["path"] or "").strip() or None
    version = (values["wm_version"] or "").strip() or None
    return Pointer(atlas, hint, version), None


def render_pointer(pointer: Pointer, *, old: bool = False) -> str:
    """The pointer's text: a ``waymark/config.toml``, or with ``old`` a ``.waymark/atlas.toml``."""
    settings = [f"atlas = {json.dumps(pointer.atlas)}"]
    if pointer.path_hint:
        settings.append(f"path = {json.dumps(pointer.path_hint)}")
    if pointer.wm_version:
        settings.append(f"wm_version = {json.dumps(pointer.wm_version)}")
    if old:
        heading = [
            "# This repository's record lives in a Waymark atlas. Written by wm atlas point."
        ]
    else:
        heading = [
            "# A pointer, not a record: this repository's record lives in the Waymark atlas",
            "# named below. Written by wm atlas point.",
            f"[{POINTER_TABLE}]",
        ]
    return "\n".join(heading + settings) + "\n"

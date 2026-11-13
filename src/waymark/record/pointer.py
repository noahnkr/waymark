"""The pointer file a code repo may carry: which atlas holds its record, and where.

It sits at ``.waymark/atlas.toml`` in the code repo's top folder and holds the
atlas's name, an optional relative-path hint and the pinned wm version. A code
repo needs no Waymark files; the pointer is written only when asked for.
"""

import json
import tomllib
from dataclasses import dataclass

POINTER_DIR = ".waymark"
POINTER_FILE = f"{POINTER_DIR}/atlas.toml"
_KEYS = frozenset({"atlas", "path", "wm_version"})


@dataclass(frozen=True)
class Pointer:
    """What a code repo's pointer file says."""

    atlas: str
    path_hint: str | None
    wm_version: str | None


def parse_pointer(text: str) -> tuple[Pointer | None, str | None]:
    """Read a pointer file. Returns the pointer, or why it can't be read."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return None, f"{POINTER_FILE} is not valid TOML: {error}."
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        return None, f'{POINTER_FILE} holds "{unknown[0]}", which is not one of its settings.'
    values = {key: data.get(key) for key in _KEYS}
    if not all(value is None or isinstance(value, str) for value in values.values()):
        return None, f"{POINTER_FILE} holds a setting that is not a string."
    atlas = (values["atlas"] or "").strip()
    if not atlas:
        return None, f'{POINTER_FILE} names no atlas. Set "atlas" to the atlas\'s name.'
    hint = (values["path"] or "").strip() or None
    version = (values["wm_version"] or "").strip() or None
    return Pointer(atlas, hint, version), None


def render_pointer(pointer: Pointer) -> str:
    """The pointer file's text."""
    lines = [
        "# This repository's record lives in a Waymark atlas. Written by wm atlas point.",
        f"atlas = {json.dumps(pointer.atlas)}",
    ]
    if pointer.path_hint:
        lines.append(f"path = {json.dumps(pointer.path_hint)}")
    if pointer.wm_version:
        lines.append(f"wm_version = {json.dumps(pointer.wm_version)}")
    return "\n".join(lines) + "\n"

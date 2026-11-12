"""A small JSON Schema validator, covering the keywords the view schemas use."""

import re
from typing import Any

_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}
_KNOWN = {
    "$schema",
    "title",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "const",
    "anyOf",
    "pattern",
}


def _is_type(value: Any, name: str) -> bool:
    if name == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[name])


def errors(value: Any, schema: dict[str, Any], where: str = "$") -> list[str]:  # noqa: PLR0912
    """Every way a value breaks a schema; empty when it is valid."""
    unknown = set(schema) - _KNOWN
    assert not unknown, f"the validator doesn't know {unknown}"
    found: list[str] = []
    if "const" in schema and value != schema["const"]:
        found.append(f"{where}: expected {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{where}: {value!r} is not one of {schema['enum']}")
    if "anyOf" in schema and all(errors(value, option, where) for option in schema["anyOf"]):
        found.append(f"{where}: matches none of the alternatives")
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, name) for name in names):
            found.append(f"{where}: {value!r} is not of type {names}")
            return found
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        found.append(f"{where}: {value!r} doesn't match {schema['pattern']}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            found += errors(item, schema["items"], f"{where}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        found += [
            f"{where}: missing {key}" for key in schema.get("required", []) if key not in value
        ]
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                found += errors(item, properties[key], f"{where}.{key}")
            elif extra is False:
                found.append(f"{where}: unexpected {key}")
            elif isinstance(extra, dict):
                found += errors(item, extra, f"{where}.{key}")
    return found

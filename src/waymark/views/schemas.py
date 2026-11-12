"""The schema of every ``--json`` payload, as JSON Schema.

Each payload names its schema and carries a version. Adding a field keeps the
version; removing or changing one bumps it.
"""

from typing import Any

from waymark.record.state import (
    AcceptanceState,
    ConflictKind,
    ExplorationStatus,
    RoadmapStatus,
    StepKind,
)
from waymark.record.tasks import RecordKind
from waymark.record.terms import Layout, Phase, ReviewLevel, Verdict
from waymark.views.payloads import KINDS, VERSIONS

Schema = dict[str, Any]

STRING: Schema = {"type": "string"}
TEXT_OR_NULL: Schema = {"type": ["string", "null"]}
INTEGER: Schema = {"type": "integer"}
BOOLEAN: Schema = {"type": "boolean"}
DATE: Schema = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
DATE_OR_NULL: Schema = {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"}
NAMES: Schema = {"type": "array", "items": STRING}
SECTIONS: Schema = {"type": "object", "additionalProperties": STRING}


def _enum(values: Any, *, nullable: bool = False) -> Schema:
    choices: list[str | None] = [str(value.value) for value in values]
    return {"enum": [*choices, None] if nullable else choices}


def _object(properties: dict[str, Schema]) -> Schema:
    """An object with exactly these properties, all required."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _array(items: Schema) -> Schema:
    return {"type": "array", "items": items}


def _nullable(schema: Schema) -> Schema:
    return {"anyOf": [schema, {"type": "null"}]}


def _payload(name: str, properties: dict[str, Schema]) -> Schema:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"wm.{name}",
        **_object(
            {
                "schema": {"const": f"wm.{name}"},
                "version": {"const": VERSIONS[name]},
                **properties,
            }
        ),
    }


CONFLICT = _object(
    {
        "kind": _enum(ConflictKind),
        "spec": STRING,
        "requirement": TEXT_OR_NULL,
        "changes": NAMES,
        "message": STRING,
    }
)

CHANGE_STATE = _object(
    {
        "name": STRING,
        "owner": TEXT_OR_NULL,
        "phase": _enum(Phase),
        "short_path": BOOLEAN,
        "acceptance": _enum(AcceptanceState),
        "ticked": INTEGER,
        "total": INTEGER,
        "next_step": _object(
            {"kind": _enum(StepKind), "item": TEXT_OR_NULL, "human": BOOLEAN, "reason": STRING}
        ),
        "conflicts": _array(CONFLICT),
    }
)

DELTA_NAMES = {"added": NAMES, "modified": NAMES, "removed": NAMES}

ITEM = _object(
    {
        "number": STRING,
        "title": STRING,
        "ticked": BOOLEAN,
        "level": _enum(ReviewLevel, nullable=True),
        "reviewed": {"type": ["boolean", "null"]},
        "needs_human": TEXT_OR_NULL,
        "criteria": TEXT_OR_NULL,
        "verify": TEXT_OR_NULL,
        "repo": TEXT_OR_NULL,
        "blocked": TEXT_OR_NULL,
        "spec_gap": TEXT_OR_NULL,
        "notes": NAMES,
        "records": _array(
            _object(
                {
                    "kind": _enum(RecordKind),
                    "date": DATE,
                    "verdict": _enum(Verdict, nullable=True),
                    "text": STRING,
                }
            )
        ),
    }
)

SCHEMAS: dict[str, Schema] = {
    "status": _payload(
        "status",
        {
            "layout": _enum(Layout),
            "atlas": TEXT_OR_NULL,
            "wm_version": STRING,
            "pinned_version": TEXT_OR_NULL,
            "writable": BOOLEAN,
            "changes": _array(CHANGE_STATE),
            "milestones": _array(
                _object({"name": STRING, "archived": INTEGER, "total": INTEGER, "planned": INTEGER})
            ),
            "needs_human": INTEGER,
            "recently_archived": _array(_object({"name": STRING, "date": DATE})),
            "problems": INTEGER,
        },
    ),
    "inbox": _payload(
        "inbox",
        {
            "entries": _array(
                _object(
                    {
                        "kind": {
                            "enum": [
                                "accept",
                                "spec-gap",
                                "verdict",
                                "blocked",
                                "conflict",
                                "archive",
                                "question",
                            ]
                        },
                        "change": TEXT_OR_NULL,
                        "item": TEXT_OR_NULL,
                        "exploration": TEXT_OR_NULL,
                        "command": TEXT_OR_NULL,
                        "summary": STRING,
                    }
                )
            )
        },
    ),
    "ls": _payload(
        "ls",
        {
            "kind": {"enum": list(KINDS)},
            "entries": _array(_object({"name": STRING, "state": STRING, "detail": STRING})),
        },
    ),
    "check": _payload(
        "check",
        {
            "findings": _array(
                _object(
                    {
                        "severity": {"enum": ["error", "warning"]},
                        "path": STRING,
                        "line": INTEGER,
                        "code": STRING,
                        "message": STRING,
                    }
                )
            ),
            "errors": INTEGER,
            "warnings": INTEGER,
        },
    ),
    "show.change": _payload(
        "show.change",
        {
            "name": STRING,
            "path": STRING,
            "archived_on": DATE_OR_NULL,
            "title": TEXT_OR_NULL,
            "state": _nullable(CHANGE_STATE),
            "owner": TEXT_OR_NULL,
            "accepted": _nullable(_object({"date": DATE, "by": STRING})),
            "synced_on": DATE_OR_NULL,
            "proposal": _nullable(SECTIONS),
            "outcome": TEXT_OR_NULL,
            "deltas": _array(_object({"spec": STRING, **DELTA_NAMES})),
            "design": _nullable(_object({"decisions": NAMES})),
            "items": _array(ITEM),
            "problems": _array(
                _object({"path": STRING, "line": INTEGER, "code": STRING, "message": STRING})
            ),
        },
    ),
    "show.spec": _payload(
        "show.spec",
        {
            "name": STRING,
            "title": STRING,
            "purpose": STRING,
            "repos": NAMES,
            "requirements": _array(
                _object(
                    {
                        "name": STRING,
                        "statement": STRING,
                        "scenarios": _array(
                            _object(
                                {
                                    "name": STRING,
                                    "steps": _array(_object({"keyword": STRING, "text": STRING})),
                                }
                            )
                        ),
                    }
                )
            ),
            "pending": _array(_object({"change": STRING, **DELTA_NAMES})),
            "history": _array(_object({"date": DATE, "change": STRING, "outcome": TEXT_OR_NULL})),
        },
    ),
    "show.milestone": _payload(
        "show.milestone",
        {
            "name": STRING,
            "title": TEXT_OR_NULL,
            "goal": _nullable(SECTIONS),
            "lines": _array(
                _object({"text": STRING, "change": TEXT_OR_NULL, "status": _enum(RoadmapStatus)})
            ),
            "archived": INTEGER,
            "total": INTEGER,
        },
    ),
    "show.exploration": _payload(
        "show.exploration",
        {
            "name": STRING,
            "title": STRING,
            "status": _enum(ExplorationStatus),
            "detail": TEXT_OR_NULL,
            "sections": SECTIONS,
        },
    ),
}
"""Every payload's schema, by the name after ``wm.`` in its ``schema`` field."""

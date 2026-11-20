"""The schema of every ``--json`` payload, as JSON Schema.

Each payload names its schema and carries a version. Adding a field keeps the
version; removing or changing one bumps it.
"""

from typing import Any

from waymark.record.evidence.records import RecordKind
from waymark.record.state import (
    AcceptanceState,
    ConflictKind,
    ExplorationStatus,
    RoadmapStatus,
    StepKind,
)
from waymark.record.terms import BuildRole, Layout, Phase, ReviewLevel, ReviewSeverity, Verdict
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
        "branch": STRING,
        "base": STRING,
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
        "repos": _array(
            _object(
                {
                    "name": STRING,
                    "kind": {"enum": ["atlas", "code"]},
                    "found": BOOLEAN,
                    "branch": TEXT_OR_NULL,
                    "matches": BOOLEAN,
                    "warn": BOOLEAN,
                }
            )
        ),
    }
)

DELTA_NAMES = {"added": NAMES, "modified": NAMES, "removed": NAMES}

RECORD = _object(
    {
        "kind": _enum(RecordKind),
        "line": STRING,
        "date": DATE,
        "by": TEXT_OR_NULL,
        "verdict": _enum(Verdict, nullable=True),
        "text": STRING,
        "item": TEXT_OR_NULL,
        "items": NAMES,
        "covers": NAMES,
        "findings": _array(
            _object({"severity": _enum(ReviewSeverity), "place": STRING, "text": STRING})
        ),
    }
)

ITEM = _object(
    {
        "number": STRING,
        "title": STRING,
        "ticked": BOOLEAN,
        "build": _enum(BuildRole, nullable=True),
        "needs_human": TEXT_OR_NULL,
        "criteria": TEXT_OR_NULL,
        "verify": TEXT_OR_NULL,
        "repo": TEXT_OR_NULL,
        "blocked": TEXT_OR_NULL,
        "spec_gap": TEXT_OR_NULL,
        "records": _array(RECORD),
    }
)

CHANGE_REVIEW = _object(
    {
        "level": _enum(ReviewLevel),
        "reviewed": {"type": ["boolean", "null"]},
        "reopen": NAMES,
        "needs_human": TEXT_OR_NULL,
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
            "default_branch": STRING,
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
            "from": TEXT_OR_NULL,
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
            "review": CHANGE_REVIEW,
            "log": _array(RECORD),
            "problems": _array(
                _object({"path": STRING, "line": INTEGER, "code": STRING, "message": STRING})
            ),
        },
    ),
    "show.spec": _payload(
        "show.spec",
        {
            "from": TEXT_OR_NULL,
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
            "archived_on": DATE_OR_NULL,
            "sections": SECTIONS,
        },
    ),
    "show.resource": _payload(
        "show.resource",
        {
            "name": STRING,
            "title": STRING,
            "kind": TEXT_OR_NULL,
            "serves": NAMES,
            "status": TEXT_OR_NULL,
            "verified": DATE_OR_NULL,
            "sections": SECTIONS,
        },
    ),
}
"""Every payload's schema, by the name after ``wm.`` in its ``schema`` field."""

_STEPS = [*(kind.value for kind in StepKind), "explore"]

_DEFINITION = {
    "number": STRING,
    "title": STRING,
    "build": _enum(BuildRole, nullable=True),
    "criteria": TEXT_OR_NULL,
    "verify": TEXT_OR_NULL,
    "repo": TEXT_OR_NULL,
    "repo_found": {"type": ["boolean", "null"]},
}
_PACK_REVIEW = _object(
    {
        "date": DATE,
        "verdict": _enum(Verdict, nullable=True),
        "text": STRING,
        "items": NAMES,
        "covers": NAMES,
        "findings": _array(
            _object({"severity": _enum(ReviewSeverity), "place": STRING, "text": STRING})
        ),
    }
)
_PACK_ITEM = _object(
    {**_DEFINITION, "notes": NAMES, "reviews": _array(_PACK_REVIEW), "resolutions": NAMES}
)
_DELTAS = _array(_object({"spec": STRING, "text": STRING}))
_BACKGROUNDS = _array(_object({"spec": STRING, "text": STRING}))


_PACK_MILESTONE = _nullable(_object({"name": STRING, "goal": STRING, "non_goals": STRING}))
_PACK_RESOURCES = _array(
    _object(
        {
            "name": STRING,
            "kind": TEXT_OR_NULL,
            "what_it_is": STRING,
            "access": STRING,
            "outline": _array(_object({"level": INTEGER, "title": STRING})),
            "command": STRING,
        }
    )
)


def _implement_pack() -> Schema:
    return _payload(
        "context.implement",
        {
            "for": {"const": "implement"},
            "change": STRING,
            "item": _PACK_ITEM,
            "context": STRING,
            "milestone": _PACK_MILESTONE,
            "resources": _PACK_RESOURCES,
            "rules": STRING,
            "proposal": _nullable(SECTIONS),
            "deltas": _DELTAS,
            "requirements": _array(_object({"spec": STRING, "name": STRING, "text": STRING})),
            "backgrounds": _BACKGROUNDS,
            "design": TEXT_OR_NULL,
            "stopping_rules": NAMES,
            "ends_with": STRING,
        },
    )


def _review_pack() -> Schema:
    return _payload(
        "context.review",
        {
            "for": {"const": "review"},
            "change": STRING,
            "review_level": _enum(ReviewLevel),
            "uncovered_only": BOOLEAN,
            "items": _array(_object(_DEFINITION)),
            "human_items": NAMES,
            "human_note": TEXT_OR_NULL,
            "reviews": _array(_PACK_REVIEW),
            "resolutions": NAMES,
            "context": STRING,
            "milestone": _PACK_MILESTONE,
            "resources": _PACK_RESOURCES,
            "rules": STRING,
            "deltas": _DELTAS,
            "backgrounds": _BACKGROUNDS,
            "design": TEXT_OR_NULL,
            "severity_rubric": NAMES,
            "ends_with": STRING,
        },
    )


SCHEMAS.update(
    {
        "instructions": _payload(
            "instructions",
            {
                "change": TEXT_OR_NULL,
                "branch": TEXT_OR_NULL,
                "base": TEXT_OR_NULL,
                "step": {"enum": _STEPS},
                "item": TEXT_OR_NULL,
                "ready": BOOLEAN,
                "reason": STRING,
                "outputs": _array(
                    _object({"path": STRING, "exists": BOOLEAN, "template": TEXT_OR_NULL})
                ),
                "rules": STRING,
                "context": STRING,
                "read": NAMES,
                "guidance": NAMES,
                "commands": NAMES,
                "unlocks": STRING,
                "checklist": _array(_object({"text": STRING, "enforced": BOOLEAN})),
                "shared_rules": NAMES,
                "severity_rubric": NAMES,
            },
        ),
        "context.explore": _payload(
            "context.explore",
            {
                "for": {"const": "explore"},
                "charter": SECTIONS,
                "rules": STRING,
                "specs": _array(
                    _object(
                        {"name": STRING, "title": STRING, "purpose": STRING, "requirements": NAMES}
                    )
                ),
                "changes": _array(
                    _object({"name": STRING, "title": STRING, "phase": _enum(Phase)})
                ),
                "milestones": _array(
                    _object({"name": STRING, "archived": INTEGER, "total": INTEGER})
                ),
                "explorations": _array(
                    _object(
                        {
                            "name": STRING,
                            "title": STRING,
                            "status": _enum(ExplorationStatus),
                            "detail": TEXT_OR_NULL,
                        }
                    )
                ),
                "references": _array(
                    _object(
                        {
                            "atlas": STRING,
                            "found": BOOLEAN,
                            "specs": _array(
                                _object({"name": STRING, "title": STRING, "purpose": STRING})
                            ),
                        }
                    )
                ),
                "resources": _array(
                    _object(
                        {
                            "name": STRING,
                            "title": STRING,
                            "kind": TEXT_OR_NULL,
                            "status": TEXT_OR_NULL,
                            "serves": NAMES,
                        }
                    )
                ),
            },
        ),
        "context.implement": _implement_pack(),
        "context.review": _review_pack(),
        "pr": _payload(
            "pr",
            {
                "change": STRING,
                "repo": TEXT_OR_NULL,
                "branch": STRING,
                "base": STRING,
                "title": STRING,
                "body": STRING,
                "links": _array(_object({"name": STRING, "url": STRING})),
            },
        ),
        "doctor": _payload(
            "doctor",
            {
                "scope": {"enum": ["project", "atlas"]},
                "ok": BOOLEAN,
                "checks": _array(
                    _object(
                        {
                            "name": STRING,
                            "status": {"enum": ["ok", "warning", "error"]},
                            "message": STRING,
                        }
                    )
                ),
            },
        ),
    }
)

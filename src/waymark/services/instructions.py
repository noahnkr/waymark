"""Instructions: what an agent does at one step of a change.

For the step asked about (by default the change's next step) this gives the
file to write and its template, the project's rules for that step, what to
read first, the commands to run and what the step unlocks. Everything comes
from the files; nothing depends on an earlier conversation.
"""

from typing import Any

from waymark.record import templates
from waymark.record.changes import DESIGN_FILE, PROPOSAL_FILE, SPECS_DIR, TASKS_FILE, Change
from waymark.record.charter import CHARTER_FILE
from waymark.record.project import RECORD_DIR
from waymark.record.record import SPECS, Record
from waymark.record.state import AcceptanceState, ChangeState, StepKind
from waymark.record.terms import Layout, ReviewLevel, Step
from waymark.services.common import Refusal, find_change, state_of

INSTRUCTIONS_VERSION = 1
EXPLORE = "explore"

_RANK = {
    StepKind.PROPOSE: 0,
    StepKind.SPECS: 1,
    StepKind.DESIGN: 2,
    StepKind.TASKS: 3,
    StepKind.RESOLVE_CONFLICT: 4,
    StepKind.ACCEPT: 4,
    StepKind.APPLY: 5,
    StepKind.REVIEW: 5,
    StepKind.RESOLVE_ITEMS: 5,
    StepKind.ARCHIVE: 6,
}

_UNLOCKS = {
    StepKind.PROPOSE: "The specs step: the deltas against the living specs.",
    StepKind.SPECS: "The design step, or the tasks step on the short path.",
    StepKind.DESIGN: "The tasks step.",
    StepKind.TASKS: "Acceptance by the human; nothing is built before it.",
    StepKind.RESOLVE_CONFLICT: "Acceptance by the human.",
    StepKind.ACCEPT: "Applying the items.",
    StepKind.APPLY: "The item's review.",
    StepKind.REVIEW: "The next item; after the last one, archiving.",
    StepKind.RESOLVE_ITEMS: "Applying the item again.",
    StepKind.ARCHIVE: "The living specs take the deltas, and the change moves to the archive.",
}

_RISK_SIGNALS = (
    "the item modifies or removes an existing requirement",
    "it touches security, data integrity or money",
    "it is being redone after a failed review",
)


def _path(relative: str) -> str:
    """A record file's path from the project's top folder."""
    return f"{RECORD_DIR}/{relative}"


def _output(record: Record, relative: str, template: str | None) -> dict[str, Any]:
    exists = "<" not in relative and record.files.is_file(relative)
    return {"path": _path(relative), "exists": exists, "template": template}


def _existing(record: Record, change: Change, *names: str) -> list[str]:
    return [
        _path(f"{change.path}/{name}")
        for name in names
        if record.files.is_file(f"{change.path}/{name}")
    ]


def _deltas(change: Change) -> list[str]:
    return [_path(delta.doc.path) for _, delta in sorted(change.deltas.items())]


def _specs(record: Record) -> list[str]:
    return [_path(f"{SPECS}/{name}.md") for name in sorted(record.specs)]


def _tasks_template(record: Record) -> str:
    text = templates.render(templates.TASKS)
    if record.layout is Layout.ATLAS:
        repos = " | ".join(sorted(record.config.repo_names)) if record.config else ""
        text = text.replace(
            "  - Verify: <how to check it>\n",
            f"  - Verify: <how to check it>\n  - Repo: <{repos or 'repo'}>\n",
        )
    return text


def _drafting(
    record: Record, change: Change, step: StepKind
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """The outputs, reading list and guidance for a step that drafts an artifact."""
    folder = change.path
    charter = _path(CHARTER_FILE)
    default = record.default_review.value
    if step is StepKind.PROPOSE:
        outputs = [_output(record, f"{folder}/{PROPOSAL_FILE}", None)]
        guidance = [
            "Fill in every section of the proposal; leave the Owner line as it is.",
            'Under Impact, name the specs the change touches, or write "No spec changes".',
            "Don't write the Accepted line or the Outcome section; wm writes the first, and "
            "the second comes at archive.",
        ]
        return outputs, [charter, *_specs(record)], guidance
    if step is StepKind.SPECS:
        outputs = [
            _output(record, f"{folder}/{SPECS_DIR}/<domain>.md", templates.render(templates.DELTA))
        ]
        guidance = [
            "Write one delta file per spec the change touches, named after the spec.",
            "A modified requirement is written out in full under its existing heading; "
            "a removed one gives a reason; a rename is a removal plus an addition.",
            "A delta that creates a spec needs a Purpose section.",
            "Every requirement states what the system SHALL do and has at least one scenario.",
        ]
        return (
            outputs,
            [charter, *_existing(record, change, PROPOSAL_FILE), *_specs(record)],
            guidance,
        )
    if step is StepKind.DESIGN:
        outputs = [_output(record, f"{folder}/{DESIGN_FILE}", templates.render(templates.DESIGN))]
        guidance = [
            "Say how the change will be built, not what it does; the deltas say that.",
            "Record each decision with its options, the choice and why.",
        ]
        read = [charter, *_existing(record, change, PROPOSAL_FILE), *_deltas(change)]
        return outputs, read, guidance
    outputs = [_output(record, f"{folder}/{TASKS_FILE}", _tasks_template(record))]
    guidance = [
        "Give every item criteria that can be checked, and say how to verify it.",
        "Number items by section and never renumber; append new items at the end.",
        f"The default review level is {default}. Tag an item only when its level differs, "
        "and suggest independent review for risky items: " + "; ".join(_RISK_SIGNALS) + ".",
        "Don't tick items or write Blocked, Spec gap or review lines; wm writes those.",
    ]
    if record.layout is Layout.ATLAS:
        guidance.append("Give every item a Repo line naming the repo it works in.")
    if change.short_path:
        guidance.append("This change is on the short path: no item may need independent review.")
    read = [
        charter,
        *_existing(record, change, PROPOSAL_FILE, DESIGN_FILE),
        *_deltas(change),
    ]
    return outputs, read, guidance


def _working(  # noqa: PLR0911 - one return per step
    change: Change, state: ChangeState, step: StepKind
) -> tuple[list[str], list[str]]:
    """The guidance and commands for a step that works on an accepted change."""
    name = change.name
    item = state.next_step.item if state.next_step.kind is step else None
    number = item or "<item>"
    if step is StepKind.APPLY:
        guidance = [
            f"Start an implementer for item {number} with the change and item and nothing else.",
            "The implementer begins from its context pack and ends with a RESULT line.",
            "If the tool has no isolated agents, build the item yourself from the same pack.",
        ]
        commands = [f"wm context {name} {number} --for implement"]
        if state.next_step.reason:
            commands.insert(0, f"wm reopen {name} {number}")
        return guidance, commands
    if step is StepKind.REVIEW:
        level = next((i.level for i in state.items if i.number == item), None)
        if level is ReviewLevel.INDEPENDENT:
            guidance = [
                f"Start a reviewer for item {number} with the change and item and nothing else.",
                "The reviewer begins from its context pack and ends with a VERDICT line.",
                "Without isolated agents, record the verdict yourself with the verdict command.",
            ]
            commands = [
                f"wm context {name} {number} --for review",
                f'wm verdict {name} {number} pass|changes|spec-gap "<reasons>"',
            ]
            return guidance, commands
        guidance = [
            f"Check item {number} against its criteria and the scenarios it serves: is it "
            "complete, correct and coherent with the rest?",
            "Then record the self-review. Commit once the review is recorded.",
        ]
        return guidance, [f'wm review {name} {number} --self "<summary>"']
    if step is StepKind.ARCHIVE:
        guidance = [
            "Archiving is the human's call: it comes after the code is merged.",
            "Say in the outcome what was built and anything that differs from the proposal.",
        ]
        return guidance, [f'wm archive {name} --outcome "<what came of it>"']
    if step is StepKind.ACCEPT:
        guidance = [
            "Only the human accepts a change. Summarize the proposal, the deltas, the design "
            "and the review levels, and ask them to run the command.",
        ]
        return guidance, [f"wm accept {name}"]
    if step is StepKind.RESOLVE_CONFLICT:
        guidance = [
            "A delta no longer applies to its spec. Revise the delta against the spec as it "
            "now reads; the human then accepts the change again.",
        ]
        return guidance, [f"wm show {name}"]
    guidance = [
        "These items wait on the human: bring each blocker, spec gap or verdict to them.",
        "Once they have decided, record the decision; the item returns to apply.",
    ]
    return guidance, [f'wm resolve {name} {number} "<what was decided>"', "wm inbox"]


def _explore(record: Record) -> dict[str, Any]:
    charter = record.charter
    return {
        "schema": "wm.instructions",
        "version": INSTRUCTIONS_VERSION,
        "change": None,
        "step": EXPLORE,
        "item": None,
        "ready": True,
        "reason": "",
        "outputs": [],
        "rules": charter.rules.get(Step.EXPLORE, "") if charter else "",
        "context": charter.context if charter else "",
        "read": [_path(CHARTER_FILE)],
        "guidance": [
            "Think the idea through with the human from the context pack. Write nothing.",
            "At the end, offer to do nothing, save an exploration, start a proposal, "
            "or start a milestone.",
        ],
        "commands": [
            "wm context --for explore",
            "wm new exploration <name>",
            "wm new change <name>",
            "wm new milestone <name>",
        ],
        "unlocks": "A saved exploration, a proposal or a milestone, if the human asks for one.",
    }


def _pick_change(record: Record, name: str | None) -> Change:
    if name is not None:
        return find_change(record, name)
    if len(record.changes) == 1:
        return next(iter(record.changes.values()))
    active = ", ".join(sorted(record.changes)) or "none"
    raise Refusal(
        f"Say which change with --change <name>. Active changes: {active}."
        if record.changes
        else 'There is no active change. Create one with "wm new change <name>".'
    )


def instructions(record: Record, step: str | None, change_name: str | None) -> dict[str, Any]:
    """What to do at a step of a change; without a step, at the change's next step."""
    if step == EXPLORE:
        return _explore(record)
    change = _pick_change(record, change_name)
    state = state_of(record, change)
    current = state.next_step
    kind = StepKind(step) if step is not None else current.kind

    ready = _RANK[kind] <= _RANK[current.kind]
    reason = current.reason if kind is current.kind else ""
    if kind is StepKind.DESIGN and change.short_path:
        ready = False
        reason = "This change is on the short path, which has no design."
    elif not ready:
        reason = (
            f'The change is at "{current.kind.value}", which comes first. {current.reason}'.strip()
        )
    elif _RANK[kind] < _RANK[StepKind.ACCEPT] and state.acceptance is AcceptanceState.VALID:
        reason = "The change is accepted: editing this artifact withdraws its acceptance."

    outputs: list[dict[str, Any]] = []
    read: list[str] = [_path(CHARTER_FILE), *_existing(record, change, PROPOSAL_FILE, TASKS_FILE)]
    commands: list[str] = []
    if _RANK[kind] <= _RANK[StepKind.TASKS]:
        outputs, read, guidance = _drafting(record, change, kind)
    else:
        guidance, commands = _working(change, state, kind)

    charter = record.charter
    rules = ""
    if charter and kind.value in set(Step):
        rules = charter.rules.get(Step(kind.value), "")
    return {
        "schema": "wm.instructions",
        "version": INSTRUCTIONS_VERSION,
        "change": change.name,
        "step": kind.value,
        "item": current.item if kind is current.kind else None,
        "ready": ready,
        "reason": reason,
        "outputs": outputs,
        "rules": rules,
        "context": charter.context if charter else "",
        "read": read,
        "guidance": guidance,
        "commands": commands,
        "unlocks": _UNLOCKS[kind],
    }

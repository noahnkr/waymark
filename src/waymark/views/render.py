"""Rendering payloads: as JSON, and as styled text.

Both read the same payload. JSON is never styled, and it is written with
ASCII escapes so that any console can carry it unharmed. Keys starting with
an underscore hold values local to this machine, such as a folder; the text
shows them and the JSON leaves them out.
"""

import json
from collections.abc import Callable
from typing import Any

from waymark.views.payloads import Payload
from waymark.views.style import ACCENT, ATTENTION, DANGER, MUTED, OK, STRONG, Style

_NAME_WIDTH = 24
_PHASE_WIDTH = 10
_INBOX_TITLES = {
    "accept": "To accept",
    "spec-gap": "Spec gaps",
    "verdict": "Verdicts that came back",
    "blocked": "Blocked items",
    "conflict": "Conflicts",
    "archive": "To archive",
    "question": "Open questions",
}


def public(value: Any) -> Any:
    """A payload without its machine-local values: what its JSON holds."""
    if isinstance(value, dict):
        return {key: public(item) for key, item in value.items() if not key.startswith("_")}
    if isinstance(value, list):
        return [public(item) for item in value]
    return value


def to_json(payload: Payload) -> str:
    """A payload as JSON text, without its machine-local values."""
    return json.dumps(public(payload), indent=2, ensure_ascii=True)


def _indent(text: str, prefix: str = "    ") -> list[str]:
    return [f"{prefix}{line}" if line else "" for line in text.split("\n")]


def _next_step(change: Payload, style: Style) -> str:
    step = change["next_step"]
    label = step["kind"] + (f" {step['item']}" if step["item"] else "")
    if step["human"]:
        return style.paint(f"{style.symbol('human')} {label} (you)", ATTENTION)
    return f"{style.symbol('arrow')} {label}"


_PHASE_ROLES = {"accepted": ACCENT, "applying": ACCENT, "applied": OK}
"""How a phase is colored: muted up to planned, accent while built, ok once applied."""


def _change_line(change: Payload, style: Style) -> str:
    name = style.paint(f"{change['name']:<{_NAME_WIDTH}}", STRONG)
    phase = style.paint(
        f"{change['phase']:<{_PHASE_WIDTH}}", _PHASE_ROLES.get(change["phase"], MUTED)
    )
    bar = style.bar(change["ticked"], change["total"])
    progress = f"{change['ticked']}/{change['total']}"
    return f"  {name} {phase} {bar} {progress:<6} {_next_step(change, style)}"


def _branch_lines(change: Payload, style: Style) -> list[str]:
    """Each repo's branch under an atlas change, and a warning for each one that differs."""
    if not change["repos"]:
        return []
    shown = ", ".join(
        f"{repo['name']} {repo['branch'] or 'no branch'}"
        if repo["found"]
        else f"{repo['name']} (not here)"
        for repo in change["repos"]
    )
    lines = [style.paint(f"      branches: {shown}", MUTED)]
    for repo in change["repos"]:
        if repo["warn"]:
            text = (
                f"      {style.symbol('warning')} {repo['name']} is on "
                f"{repo['branch'] or 'no branch'}, not on {change['name']}"
            )
            lines.append(style.paint(text, ATTENTION))
    return lines


def _roadmap_marks(archived: int, total: int, style: Style) -> str:
    """One mark per roadmap line: filled for an archived change, open for the rest."""
    done = [style.symbol("milestone_done")] * archived
    open_ = [style.symbol("milestone_open")] * max(0, total - archived)
    return " ".join([style.paint(" ".join(done), OK), style.paint(" ".join(open_), MUTED)]).strip()


def status(payload: Payload, style: Style) -> str:
    """The status view as text."""
    lines: list[str] = []
    if payload["pinned_version"] and not payload["writable"]:
        note = (
            f"{style.symbol('warning')} This is wm {payload['wm_version']}; the project is pinned "
            f"to {payload['pinned_version']}. Reading works; writing is refused."
        )
        lines += [style.paint(note, ATTENTION), ""]
    lines.append(style.rule("Changes in flight"))
    if payload["changes"]:
        for change in payload["changes"]:
            lines.append(_change_line(change, style))
            if change["base"] != payload["default_branch"]:
                lines.append(style.paint(f"{' ' * (_NAME_WIDTH + 3)}on {change['base']}", MUTED))
            lines += _branch_lines(change, style)
            lines += [
                style.paint(f"      {style.symbol('warning')} {conflict['message']}", ATTENTION)
                for conflict in change["conflicts"]
            ]
    else:
        lines.append("  None. Start one with: wm new change <name>")
    if payload["milestones"]:
        lines += ["", style.rule("Open milestones")]
        for milestone in payload["milestones"]:
            name = style.paint(f"{milestone['name']:<{_NAME_WIDTH}}", STRONG)
            bar = _roadmap_marks(
                milestone["archived"], milestone["total"] + milestone["planned"], style
            )
            detail = f"{milestone['archived']}/{milestone['total']} changes archived"
            if milestone["planned"]:
                detail += f", {milestone['planned']} not proposed yet"
            lines.append(f"  {name} {bar} {detail}")
    lines.append("")
    needs = payload["needs_human"]
    if needs:
        text = (
            f"{style.symbol('human')} {needs} "
            f"{'thing needs' if needs == 1 else 'things need'} you: wm inbox"
        )
        lines.append(style.paint(text, ATTENTION))
    else:
        lines.append(style.paint(f"{style.symbol('done')} Nothing needs you.", OK))
    if payload["problems"]:
        count = payload["problems"]
        plural = "s" if count != 1 else ""
        text = f"{style.symbol('error')} {count} problem{plural} in the record: wm check"
        lines.append(style.paint(text, DANGER))
    if payload["recently_archived"]:
        lines += ["", style.rule("Recently archived")]
        lines += [
            f"  {style.paint(entry['date'], MUTED)}  {entry['name']}"
            for entry in payload["recently_archived"]
        ]
    return "\n".join(lines)


def inbox(payload: Payload, style: Style) -> str:
    """The inbox view as text."""
    entries = payload["entries"]
    if not entries:
        return style.paint(f"{style.symbol('done')} Nothing needs you.", OK)
    lines: list[str] = []
    for kind, title in _INBOX_TITLES.items():
        group = [entry for entry in entries if entry["kind"] == kind]
        if not group:
            continue
        if lines:
            lines.append("")
        lines.append(style.rule(title))
        for entry in group:
            subject = entry["change"] or entry["exploration"]
            where = f"{subject} {entry['item']}" if entry["item"] else subject
            lines.append(f"  {style.symbol('human')} {style.paint(where, STRONG)}")
            lines.append(style.wrap(entry["summary"], "      "))
            if entry["command"]:
                lines.append(
                    style.paint(f"      {style.symbol('arrow')} {entry['command']}", ACCENT)
                )
    return "\n".join(lines)


def check(payload: Payload, style: Style) -> str:
    """The health check as text: the findings grouped under each file, then the counts."""
    lines: list[str] = []
    paths = list(dict.fromkeys(finding["path"] for finding in payload["findings"]))
    for path in paths:
        lines.append(style.paint(path, STRONG))
        for finding in payload["findings"]:
            if finding["path"] != path:
                continue
            severity = style.paint(
                finding["severity"], DANGER if finding["severity"] == "error" else ATTENTION
            )
            where = f"{finding['line']}: " if finding["line"] else ""
            lead = f"{where}{finding['code']}: "
            # On a terminal the message wraps, its lines hung under where it starts.
            hang = " " * len(f"  {finding['severity']}: {lead}")
            message = style.wrap(finding["message"], hang)[len(hang) :]
            lines.append(f"  {severity}: {lead}{message}")
    if payload["findings"]:
        worst = DANGER if payload["errors"] else ATTENTION
        counts = f"{payload['errors']} error(s), {payload['warnings']} warning(s)."
        lines.append(style.paint(counts, worst))
    else:
        lines.append(style.paint(f"{style.symbol('done')} The record is healthy.", OK))
    return "\n".join(lines)


def ls(payload: Payload, style: Style) -> str:
    """One line per entry."""
    source = f" in the atlas {payload['from']}" if payload["from"] else ""
    if not payload["entries"]:
        return f"No {payload['kind']}s{source}."
    width = max(len(entry["name"]) for entry in payload["entries"])
    states = max(len(entry["state"]) for entry in payload["entries"])
    lines: list[str] = []
    for entry in payload["entries"]:
        name = style.paint(entry["name"].ljust(width), STRONG)
        detail = style.paint(entry["detail"], MUTED)
        lines.append(f"{name}  {entry['state'].ljust(states)}  {detail}".rstrip())
    return "\n".join(lines)


def _titled(title: str, text: str | None, style: Style, *, wrap: bool = False) -> list[str]:
    """A titled section; ``wrap`` wraps its prose to the terminal, for the show views."""
    if not text:
        return []
    body = style.wrap(text, "  ").split("\n") if wrap else _indent(text, "  ")
    return ["", style.paint(title, STRONG), *body]


def _painted(text: str, style: Style, *roles: str) -> list[str]:
    """Each line of wrapped text, painted on its own so a color never spans a line break."""
    return [style.paint(line, *roles) for line in text.split("\n")]


def _item_lines(item: Payload, style: Style, *, last: bool) -> list[str]:
    """One item of a change's tree: its head on a branch, everything under it on the stem."""
    mark = style.symbol("done") if item["ticked"] else style.symbol("todo")
    tags = ["build: delegate"] if item["delegate"] else []
    if item["repo"]:
        tags.append(f"repo: {item['repo']}")
    branch = style.symbol("last" if last else "branch")
    stem = "      " if last else f"  {style.symbol('stem')}   "
    head = f"  {branch} {mark} {style.paint(item['number'], STRONG)} {item['title']}"
    lines = [head + (style.paint(f"   ({', '.join(tags)})", MUTED) if tags else "")]
    for label, key in (("Criteria", "criteria"), ("Verify", "verify")):
        if item[key]:
            if item[key].startswith("- "):
                # A list starts on the line after its label, so every bullet hangs alike.
                lines.append(f"{stem}{label}:")
                lines += style.wrap(item[key], stem + "  ").split("\n")
            else:
                lines += style.wrap(f"{label}: {item[key]}", stem).split("\n")
    for label, key, color in (
        ("Blocked", "blocked", ATTENTION),
        ("Spec gap", "spec_gap", ATTENTION),
        ("Needs you", "needs_human", ATTENTION),
    ):
        if item[key]:
            lines += _painted(style.wrap(f"{label}: {item[key]}", stem), style, color)
    for record in item["records"]:
        lines += _record_lines(record, stem, style)
    return lines


def _record_lines(record: Payload, indent: str, style: Style) -> list[str]:
    verdict = f" {record['verdict']}" if record["verdict"] else ""
    named = f" {' '.join(record['items'])}" if record["items"] else ""
    covers = f" covers {' '.join(record['covers'])}" if record.get("covers") else ""
    text = f": {record['text']}" if record["text"] else ""
    by = f" by {record['by']}" if record["by"] else ""
    head = f"({record['kind']}) {record['date']}{verdict}{named}{covers}{by}{text}"
    lines = _painted(style.wrap(head, indent), style, MUTED)
    for finding in record["findings"]:
        color = DANGER if finding["severity"] == "critical" else ATTENTION
        line = f"  {finding['severity']} `{finding['place']}`: {finding['text']}"
        lines += _painted(style.wrap(line, indent), style, color)
    return lines


def _review_section(review: Payload, style: Style) -> list[str]:
    status = {True: "reviewed", False: "not reviewed yet", None: ""}[review["reviewed"]]
    head = f"  Level: {review['level']}" + (f"; {status}" if status else "")
    lines = ["", style.paint("Review", STRONG), head]
    if review["reopen"]:
        lines.append(style.paint(f"  To rebuild: {', '.join(review['reopen'])}", ATTENTION))
    if review["needs_human"]:
        lines.append(style.paint(f"  Needs you: {review['needs_human']}", ATTENTION))
    return lines


def _log_section(log: list[Payload], style: Style) -> list[str]:
    if not log:
        return []
    lines = ["", style.paint("Log", STRONG)]
    for record in log:
        lines += _record_lines(record, "  ", style)
    return lines


def _delta_names(delta: Payload) -> str:
    parts = [
        f"{label} {', '.join(delta[key])}"
        for label, key in (("adds", "added"), ("modifies", "modified"), ("removes", "removed"))
        if delta[key]
    ]
    return "; ".join(parts) or "purpose or repos only"


def show_change(payload: Payload, style: Style) -> str:  # noqa: PLR0912 - one part per section
    """Everything about one change, as text."""
    lines = [style.rule(f"Change: {payload['name']}")]
    state = payload["state"]
    if payload["archived_on"]:
        lines.append(f"  Archived on {payload['archived_on']}")
    if state:
        lines.append(_change_line(state, style))
        lines += _branch_lines(state, style)
    facts = [f"Owner: {payload['owner'] or 'none'}"]
    if state and state["short_path"]:
        facts.append("short path")
    if payload["accepted"]:
        facts.append(f"accepted {payload['accepted']['date']} by {payload['accepted']['by']}")
    if state and state["acceptance"] == "withdrawn":
        facts.append("acceptance withdrawn")
    if payload["synced_on"]:
        facts.append(f"synced {payload['synced_on']}")
    lines.append(f"  {'; '.join(facts)}")
    if state and state["next_step"]["reason"]:
        lines.append(f"  {state['next_step']['reason']}")
    for conflict in state["conflicts"] if state else []:
        lines.append(style.paint(f"  {style.symbol('warning')} {conflict['message']}", ATTENTION))
    for title, text in (payload["proposal"] or {}).items():
        lines += _titled(title, text, style, wrap=True)
    lines += _titled("Outcome", payload["outcome"], style, wrap=True)
    if payload["deltas"]:
        lines += ["", style.paint("Deltas", STRONG)]
        lines += [f"  {delta['spec']}: {_delta_names(delta)}" for delta in payload["deltas"]]
    if payload["design"]:
        decisions = ", ".join(payload["design"]["decisions"]) or "none"
        lines += ["", style.paint("Design", STRONG), f"  Decisions: {decisions}"]
    if payload["items"]:
        lines += ["", style.paint("Tasks", STRONG)]
        for index, item in enumerate(payload["items"]):
            lines += _item_lines(item, style, last=index == len(payload["items"]) - 1)
        lines += _review_section(payload["review"], style)
    lines += _log_section(payload["log"], style)
    if payload["problems"]:
        lines += ["", style.paint("Problems", STRONG)]
        lines += [
            style.paint(f"  {p['path']}:{p['line']}: {p['message']}", DANGER)
            for p in payload["problems"]
        ]
    return "\n".join(lines)


def show_spec(payload: Payload, style: Style) -> str:
    """A spec with its pending deltas and its history, as text."""
    source = f" (from the atlas {payload['from']}, read only)" if payload["from"] else ""
    lines = [style.rule(f"Spec: {payload['name']}{source}"), f"  {payload['title']}"]
    if payload["repos"]:
        lines.append(f"  Repos: {', '.join(payload['repos'])}")
    lines += _titled("Purpose", payload["purpose"], style, wrap=True)
    lines += ["", style.paint("Requirements", STRONG)]
    for requirement in payload["requirements"]:
        lines.append(f"  {style.symbol('bullet')} {style.paint(requirement['name'], STRONG)}")
        lines += _indent(requirement["statement"], "      ")
        for scenario in requirement["scenarios"]:
            lines.append(style.paint(f"      Scenario: {scenario['name']}", MUTED))
            lines += [f"        {step['keyword']} {step['text']}" for step in scenario["steps"]]
    if not payload["requirements"]:
        lines.append("  None.")
    if payload["pending"]:
        lines += ["", style.paint("Pending deltas from active changes", STRONG)]
        lines += [f"  {delta['change']}: {_delta_names(delta)}" for delta in payload["pending"]]
    if payload["history"]:
        lines += ["", style.paint("History", STRONG)]
        for entry in payload["history"]:
            lines.append(f"  {style.paint(entry['date'], MUTED)}  {entry['change']}")
            lines += _indent(entry["outcome"] or "", "      ") if entry["outcome"] else []
    return "\n".join(lines)


def show_milestone(payload: Payload, style: Style) -> str:
    """A milestone with its roadmap, as text."""
    lines = [style.rule(f"Milestone: {payload['name']}")]
    bar = style.bar(payload["archived"], payload["total"])
    lines.append(f"  {bar} {payload['archived']}/{payload['total']} changes archived")
    for title, text in (payload["goal"] or {}).items():
        lines += _titled(title, text, style, wrap=True)
    lines += ["", style.paint("Roadmap", STRONG)]
    for line in payload["lines"]:
        if line["status"] == "archived":
            mark = style.paint(style.symbol("milestone_done"), OK)
        elif line["status"] == "active":
            mark = style.symbol("milestone_open")
        else:
            mark = style.paint(style.symbol("todo"), MUTED)
        status_text = style.paint(f"({line['status']})", MUTED)
        lines.append(f"  {mark} {line['change'] or line['text']} {status_text}")
    if not payload["lines"]:
        lines.append("  Empty.")
    return "\n".join(lines)


def show_exploration(payload: Payload, style: Style) -> str:
    """An exploration, as text."""
    lines = [style.rule(f"Exploration: {payload['name']}"), f"  {payload['title']}"]
    detail = f": {payload['detail']}" if payload["detail"] else ""
    lines.append(f"  {payload['status']}{detail}")
    for title, text in payload["sections"].items():
        lines += _titled(title, text, style, wrap=True)
    return "\n".join(lines)


def show_resource(payload: Payload, style: Style) -> str:
    """A resource, as text: its lines at the top, then every section."""
    lines = [style.rule(f"Resource: {payload['name']}"), f"  {payload['title']}"]
    lines.append(f"  Kind: {payload['kind'] or 'unknown'}")
    lines.append(f"  Serves: {', '.join(payload['serves']) or 'none'}")
    lines.append(f"  Status: {payload['status'] or 'unknown'}")
    lines.append(f"  Verified: {payload['verified'] or 'unknown'}")
    for title, text in payload["sections"].items():
        lines += _titled(title, text, style)
    return "\n".join(lines)


def _fenced(text: str) -> list[str]:
    """Record text quoted whole, so its own headings don't mix with the pack's."""
    return ["````markdown", *text.split("\n"), "````"]


def instructions(payload: Payload, style: Style) -> str:
    """Instructions for one step, as text an agent or a person can follow."""
    subject = f" for {payload['change']}" if payload["change"] else ""
    item = f" {payload['item']}" if payload["item"] else ""
    lines = [style.rule(f"Step: {payload['step']}{item}{subject}")]
    if not payload["ready"]:
        lines.append(
            style.paint(f"  {style.symbol('warning')} Not yet: {payload['reason']}", ATTENTION)
        )
    elif payload["reason"]:
        lines.append(f"  {payload['reason']}")
    if payload.get("branch"):
        lines.append(f"  Branch {payload['branch']}, based on {payload['base']}.")
    if payload["shared_rules"]:
        lines += ["", style.paint("Shared rules", STRONG)]
        lines += [f"  {style.symbol('bullet')} {text}" for text in payload["shared_rules"]]
    if payload["guidance"]:
        lines += ["", style.paint("What to do", STRONG)]
        lines += [f"  {style.symbol('bullet')} {text}" for text in payload["guidance"]]
    if payload["checklist"]:
        lines += ["", style.paint("Checklist", STRONG)]
        lines += [
            f"  {'wm ' if check['enforced'] else '[ ]'} {check['text']}"
            for check in payload["checklist"]
        ]
    if payload["severity_rubric"]:
        lines += ["", style.paint("Severity rubric", STRONG)]
        lines += [f"  {style.symbol('bullet')} {rule}" for rule in payload["severity_rubric"]]
    if payload["commands"]:
        lines += ["", style.paint("Commands", STRONG)]
        lines += [style.paint(f"  {command}", ACCENT) for command in payload["commands"]]
    lines += _titled("Project rules", payload["rules"], style)
    lines += _titled("Project context", payload["context"], style)
    if payload["read"]:
        lines += ["", style.paint("Read first", STRONG)]
        lines += [f"  {path}" for path in payload["read"]]
    for output in payload["outputs"]:
        state = "exists; revise it" if output["exists"] else "to write"
        lines += ["", style.paint(f"Write: {output['path']}", STRONG) + f"  ({state})"]
        if output["template"]:
            lines += ["  Template:", *_indent(output["template"].rstrip("\n"), "  | ")]
    lines += ["", f"{style.paint('Unlocks', STRONG)}: {payload['unlocks']}"]
    return "\n".join(lines)


def _definition_lines(item: Payload) -> list[str]:
    lines = [f"**{item['number']} {item['title']}**", ""]
    for label, key in (("Criteria", "criteria"), ("Verify", "verify")):
        if item[key]:
            lines.append(f"- {label}: {item[key]}")
    if item["repo"]:
        folder = item["_local"]["repo_folder"]
        where = f"its folder on this machine is {folder}" if folder else "not found on this machine"
        lines.append(f"- Repo: {item['repo']} ({where})")
    return lines


def _review_lines(review: Payload) -> list[str]:
    named = f" {' '.join(review['items'])}" if review["items"] else ""
    covers = f", covers {' '.join(review['covers'])}" if review["covers"] else ""
    head = f"({review['date']}, {review['verdict']}{named}{covers})"
    lines = [f"- Earlier review {head}: {review['text']}"]
    lines += [
        f"  - {finding['severity']}: {finding['place']}: {finding['text']}"
        for finding in review["findings"]
    ]
    return lines


def _pack_item(item: Payload) -> list[str]:
    lines = _definition_lines(item)
    lines += [f"- Decided by the human: {text}" for text in item["resolutions"]]
    for review in item["reviews"]:
        lines += _review_lines(review)
    lines += [f"- Note from earlier work: {note}" for note in item["notes"]]
    return lines


def _review_head(payload: Payload) -> list[str]:
    lines = [f"# Context pack: review {payload['change']}", ""]
    if payload["uncovered_only"]:
        lines += [
            f"Review only the items below, at level {payload['review_level']}: no passing "
            "review covers them, while the earlier reviews cover the rest of the change.",
            "",
        ]
    else:
        lines += [f"Review the whole change at level {payload['review_level']}.", ""]
    lines.append("## Its items")
    for item in payload["items"]:
        lines += ["", *_definition_lines(item)]
    if payload["reviews"] or payload["resolutions"]:
        lines += ["", "## Earlier reviews", ""]
        for review in payload["reviews"]:
            lines += _review_lines(review)
        lines += [f"- Decided by the human: {text}" for text in payload["resolutions"]]
    return lines


def _listed(title: str, rules: list[str]) -> list[str]:
    """A markdown section holding a list of rules, or nothing when there are none."""
    return ["", f"## {title}", "", *(f"- {rule}" for rule in rules)] if rules else []


def context_delegated(payload: Payload, _: Style) -> str:
    """An implementer's or reviewer's context pack, as markdown."""
    role = payload["for"]
    if role == "review":
        lines = _review_head(payload)
    else:
        item = payload["item"]
        lines = [f"# Context pack: {role} {payload['change']} {item['number']}", ""]
        lines += ["## Your item", "", *_pack_item(item)]
    if payload["context"]:
        lines += ["", "## Project context", "", payload["context"]]
    if payload["milestone"]:
        milestone = payload["milestone"]
        lines += ["", "## Milestone", "", f"This change works toward `{milestone['name']}`."]
        lines += ["", "### Goal", "", milestone["goal"], "", "### Non-goals", ""]
        lines.append(milestone["non_goals"])
    lines += _resource_lines(payload["resources"])
    if payload["rules"]:
        lines += ["", "## Project rules", "", payload["rules"]]
    if payload.get("proposal"):
        lines += ["", "## Proposal"]
        for title, text in payload["proposal"].items():
            lines += ["", f"### {title}", "", text]
    if payload["deltas"]:
        lines += ["", "## Deltas"]
        for delta in payload["deltas"]:
            lines += ["", f"### Spec: {delta['spec']}", "", *_fenced(delta["text"])]
    lines += _spec_lines(payload)
    if payload["design"]:
        lines += ["", "## Design", "", *_fenced(payload["design"])]
    lines += _listed("Severity rubric", payload.get("severity_rubric", []))
    lines += _listed("When to stop", payload.get("stopping_rules", []))
    lines += ["", "## How to finish", "", payload["ends_with"]]
    return "\n".join(lines)


def _spec_lines(payload: Payload) -> list[str]:
    """The living requirements the change touches, then each touched spec's Background."""
    lines: list[str] = []
    if payload.get("requirements"):
        lines += ["", "## Requirements as they stand today"]
        for requirement in payload["requirements"]:
            title = f"### {requirement['spec']}: {requirement['name']}"
            lines += ["", title, "", *_fenced(requirement["text"])]
    if payload.get("backgrounds"):
        lines += ["", "## Background"]
        for background in payload["backgrounds"]:
            lines += ["", f"### {background['spec']}", "", background["text"]]
    return lines


def context_explore(payload: Payload, _: Style) -> str:
    """The explore context pack, as markdown."""
    lines = ["# Context pack: explore"]
    for title, text in payload["charter"].items():
        # The Rules are shown once, under "Project rules", as in every other pack.
        if text and title != "Rules":
            lines += ["", f"## {title}", "", text]
    if payload["rules"]:
        lines += ["", "## Project rules", "", payload["rules"]]
    lines += ["", "## Specs", ""]
    for spec in payload["specs"]:
        names = ", ".join(spec["requirements"]) or "no requirements"
        lines.append(f"- {spec['name']}: {spec['purpose']} ({names})")
    if not payload["specs"]:
        lines.append("None yet.")
    lines += ["", "## Changes in flight", ""]
    lines += [
        f"- {change['name']} ({change['phase']}): {change['title']}"
        for change in payload["changes"]
    ] or ["None."]
    if payload["milestones"]:
        lines += ["", "## Open milestones", ""]
        lines += [
            f"- {m['name']}: {m['archived']}/{m['total']} changes archived"
            for m in payload["milestones"]
        ]
    for reference in payload["references"]:
        lines += ["", f"## Specs in the atlas {reference['atlas']} (read only)", ""]
        if not reference["found"]:
            lines.append("Not found on this machine; wm doctor says why.")
        for spec in reference["specs"]:
            lines.append(f"- {spec['name']}: {spec['purpose']}")
        if reference["found"]:
            lines += ["", f"Read one with: wm show <spec> --from {reference['atlas']}"]
    if payload["explorations"]:
        lines += ["", "## Explorations", ""]
        for exploration in payload["explorations"]:
            detail = f": {exploration['detail']}" if exploration["detail"] else ""
            lines.append(
                f"- {exploration['name']} ({exploration['status']}{detail}): {exploration['title']}"
            )
    lines += _resource_index(payload["resources"])
    return "\n".join(lines)


def _resource_index(resources: list[Payload]) -> list[str]:
    """Every resource, one line each, for the explore pack."""
    if not resources:
        return []
    lines = ["", "## Resources", ""]
    for resource in resources:
        serves = ", ".join(resource["serves"]) or "none"
        lines.append(
            f"- {resource['name']} ({resource['kind'] or 'unknown'}, "
            f"{resource['status'] or 'unknown'}, serves {serves}): {resource['title']}"
        )
    return [*lines, "", "Read one with: wm show <resource> --kind resource"]


def _resource_lines(resources: list[Payload]) -> list[str]:
    """The resources serving a change's specs: what each is, how to reach it, and the rest."""
    if not resources:
        return []
    lines = ["", "## Resources"]
    for resource in resources:
        lines += ["", f"### {resource['name']} ({resource['kind'] or 'unknown'})"]
        lines += ["", "What it is:", "", resource["what_it_is"] or "None."]
        lines += ["", "Access:", "", resource["access"] or "None."]
        lines += ["", "Its other headings:", ""]
        lines += [
            f"{'  ' * (heading['level'] - 2)}- {heading['title']}"
            for heading in resource["outline"]
        ]
        lines += ["", f"Read it in full with: {resource['command']}"]
    return lines


def doctor(payload: Payload, style: Style) -> str:
    """What a doctor found: one line per check, then the verdict."""
    marks = {"ok": ("done", OK), "warning": ("warning", ATTENTION), "error": ("error", DANGER)}
    lines: list[str] = []
    width = max((len(check["name"]) for check in payload["checks"]), default=0) + 1
    for check in payload["checks"]:
        symbol, color = marks[check["status"]]
        head = f"{style.symbol(symbol)} {check['name'] + ':':<{width}}"
        hang = " " * (len(head) + 1)
        message = style.wrap(check["message"], hang)[len(hang) :]
        lines.append(f"{style.paint(head, color)} {message}")
        if check["_folder"]:
            lines.append(style.paint(f"    {check['_folder']}", MUTED))
    errors = sum(1 for check in payload["checks"] if check["status"] == "error")
    warnings = sum(1 for check in payload["checks"] if check["status"] == "warning")
    lines.append(f"{errors} error(s), {warnings} warning(s). Nothing was changed.")
    return "\n".join(lines)


def pr(payload: Payload, style: Style) -> str:
    """A pull request's title and description, ready to paste or hand to the host's tool."""
    where = f" in {payload['repo']}" if payload["repo"] else ""
    head = style.rule(
        f"Pull request for {payload['change']}{where}, from {payload['branch']} "
        f"into {payload['base']}"
    )
    return "\n".join([head, "", f"Title: {payload['title']}", "", payload["body"].rstrip("\n")])


_RENDERERS: dict[str, Callable[[Payload, Style], str]] = {
    "wm.status": status,
    "wm.inbox": inbox,
    "wm.check": check,
    "wm.ls": ls,
    "wm.show.change": show_change,
    "wm.show.spec": show_spec,
    "wm.show.milestone": show_milestone,
    "wm.show.exploration": show_exploration,
    "wm.show.resource": show_resource,
    "wm.instructions": instructions,
    "wm.context.explore": context_explore,
    "wm.context.implement": context_delegated,
    "wm.context.review": context_delegated,
    "wm.doctor": doctor,
    "wm.pr": pr,
}


def to_text(payload: Payload, style: Style) -> str:
    """A payload as styled text, chosen by its schema."""
    return _RENDERERS[payload["schema"]](payload, style)

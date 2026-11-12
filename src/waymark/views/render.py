"""Rendering payloads: as JSON, and as styled text.

Both read the same payload. JSON is never styled, and it is written with
ASCII escapes so that any console can carry it unharmed.
"""

import json
from collections.abc import Callable

from waymark.views.payloads import Payload
from waymark.views.style import BOLD, CYAN, DIM, GREEN, RED, YELLOW, Style

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


def to_json(payload: Payload) -> str:
    """A payload as JSON text."""
    return json.dumps(payload, indent=2, ensure_ascii=True)


def _indent(text: str, prefix: str = "    ") -> list[str]:
    return [f"{prefix}{line}" if line else "" for line in text.split("\n")]


def _next_step(change: Payload, style: Style) -> str:
    step = change["next_step"]
    label = step["kind"] + (f" {step['item']}" if step["item"] else "")
    if step["human"]:
        return style.paint(f"{style.symbol('human')} {label} (you)", YELLOW)
    return f"{style.symbol('arrow')} {label}"


def _change_line(change: Payload, style: Style) -> str:
    name = style.paint(f"{change['name']:<{_NAME_WIDTH}}", BOLD)
    phase = f"{change['phase']:<{_PHASE_WIDTH}}"
    bar = style.bar(change["ticked"], change["total"])
    progress = f"{change['ticked']}/{change['total']}"
    return f"  {name} {phase} {bar} {progress:<6} {_next_step(change, style)}"


def status(payload: Payload, style: Style) -> str:
    """The status view as text."""
    lines: list[str] = []
    if payload["pinned_version"] and not payload["writable"]:
        note = (
            f"{style.symbol('warning')} This is wm {payload['wm_version']}; the project is pinned "
            f"to {payload['pinned_version']}. Reading works; writing is refused."
        )
        lines += [style.paint(note, YELLOW), ""]
    lines.append(style.rule("Changes in flight"))
    if payload["changes"]:
        for change in payload["changes"]:
            lines.append(_change_line(change, style))
            lines += [
                style.paint(f"      {style.symbol('warning')} {conflict['message']}", YELLOW)
                for conflict in change["conflicts"]
            ]
    else:
        lines.append("  None. Start one with: wm new change <name>")
    if payload["milestones"]:
        lines += ["", style.rule("Open milestones")]
        for milestone in payload["milestones"]:
            name = style.paint(f"{milestone['name']:<{_NAME_WIDTH}}", BOLD)
            bar = style.bar(milestone["archived"], milestone["total"])
            detail = f"{milestone['archived']}/{milestone['total']} changes archived"
            if milestone["planned"]:
                detail += f", {milestone['planned']} not proposed yet"
            lines.append(f"  {name} {bar} {detail}")
    lines.append("")
    needs = payload["needs_human"]
    if needs:
        text = (
            f"{style.symbol('human')} {needs} thing{'s' if needs != 1 else ''} need you: wm inbox"
        )
        lines.append(style.paint(text, YELLOW))
    else:
        lines.append(style.paint(f"{style.symbol('done')} Nothing needs you.", GREEN))
    if payload["problems"]:
        count = payload["problems"]
        plural = "s" if count != 1 else ""
        text = f"{style.symbol('error')} {count} problem{plural} in the record: wm check"
        lines.append(style.paint(text, RED))
    if payload["recently_archived"]:
        lines += ["", style.rule("Recently archived")]
        lines += [
            f"  {style.paint(entry['date'], DIM)}  {entry['name']}"
            for entry in payload["recently_archived"]
        ]
    return "\n".join(lines)


def inbox(payload: Payload, style: Style) -> str:
    """The inbox view as text."""
    entries = payload["entries"]
    if not entries:
        return style.paint(f"{style.symbol('done')} Nothing needs you.", GREEN)
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
            lines.append(f"  {style.symbol('human')} {style.paint(where, BOLD)}")
            lines += _indent(entry["summary"], "      ")
            if entry["command"]:
                lines.append(style.paint(f"      {style.symbol('arrow')} {entry['command']}", CYAN))
    return "\n".join(lines)


def check(payload: Payload, style: Style) -> str:
    """The health check as text: one line per finding, then the counts."""
    lines: list[str] = []
    for finding in payload["findings"]:
        where = finding["path"] + (f":{finding['line']}" if finding["line"] else "")
        severity = style.paint(
            finding["severity"], RED if finding["severity"] == "error" else YELLOW
        )
        lines.append(f"{severity}: {where}: {finding['code']}: {finding['message']}")
    if payload["findings"]:
        lines.append(f"{payload['errors']} error(s), {payload['warnings']} warning(s).")
    else:
        lines.append(style.paint(f"{style.symbol('done')} The record is healthy.", GREEN))
    return "\n".join(lines)


def ls(payload: Payload, style: Style) -> str:
    """One line per entry."""
    if not payload["entries"]:
        return f"No {payload['kind']}s."
    width = max(len(entry["name"]) for entry in payload["entries"])
    states = max(len(entry["state"]) for entry in payload["entries"])
    lines: list[str] = []
    for entry in payload["entries"]:
        name = style.paint(entry["name"].ljust(width), BOLD)
        detail = style.paint(entry["detail"], DIM)
        lines.append(f"{name}  {entry['state'].ljust(states)}  {detail}".rstrip())
    return "\n".join(lines)


def _titled(title: str, text: str | None, style: Style) -> list[str]:
    if not text:
        return []
    return ["", style.paint(title, BOLD), *_indent(text, "  ")]


def _item_lines(item: Payload, style: Style) -> list[str]:
    mark = style.symbol("done") if item["ticked"] else style.symbol("todo")
    tags = [f"review: {item['level']}"] if item["level"] else []
    if item["reviewed"]:
        tags.append("reviewed")
    if item["repo"]:
        tags.append(f"repo: {item['repo']}")
    head = f"  {mark} {style.paint(item['number'], BOLD)} {item['title']}"
    lines = [head + (style.paint(f"   ({', '.join(tags)})", DIM) if tags else "")]
    for label, key in (("Criteria", "criteria"), ("Verify", "verify")):
        if item[key]:
            lines.append(f"      {label}: {item[key]}".replace("\n", "\n        "))
    for label, key, color in (
        ("Blocked", "blocked", YELLOW),
        ("Spec gap", "spec_gap", YELLOW),
        ("Needs you", "needs_human", YELLOW),
    ):
        if item[key]:
            lines.append(style.paint(f"      {label}: {item[key]}", color))
    lines += [f"      Note: {note}" for note in item["notes"]]
    for record in item["records"]:
        verdict = f" {record['verdict']}" if record["verdict"] else ""
        text = f": {record['text']}" if record["text"] else ""
        lines.append(style.paint(f"      ({record['kind']}) {record['date']}{verdict}{text}", DIM))
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
        lines.append(style.paint(f"  {style.symbol('warning')} {conflict['message']}", YELLOW))
    for title, text in (payload["proposal"] or {}).items():
        lines += _titled(title, text, style)
    lines += _titled("Outcome", payload["outcome"], style)
    if payload["deltas"]:
        lines += ["", style.paint("Deltas", BOLD)]
        lines += [f"  {delta['spec']}: {_delta_names(delta)}" for delta in payload["deltas"]]
    if payload["design"]:
        decisions = ", ".join(payload["design"]["decisions"]) or "none"
        lines += ["", style.paint("Design", BOLD), f"  Decisions: {decisions}"]
    if payload["items"]:
        lines += ["", style.paint("Tasks", BOLD)]
        for item in payload["items"]:
            lines += _item_lines(item, style)
    if payload["problems"]:
        lines += ["", style.paint("Problems", BOLD)]
        lines += [
            style.paint(f"  {p['path']}:{p['line']}: {p['message']}", RED)
            for p in payload["problems"]
        ]
    return "\n".join(lines)


def show_spec(payload: Payload, style: Style) -> str:
    """A spec with its pending deltas and its history, as text."""
    lines = [style.rule(f"Spec: {payload['name']}"), f"  {payload['title']}"]
    if payload["repos"]:
        lines.append(f"  Repos: {', '.join(payload['repos'])}")
    lines += _titled("Purpose", payload["purpose"], style)
    lines += ["", style.paint("Requirements", BOLD)]
    for requirement in payload["requirements"]:
        lines.append(f"  {style.symbol('bullet')} {style.paint(requirement['name'], BOLD)}")
        lines += _indent(requirement["statement"], "      ")
        for scenario in requirement["scenarios"]:
            lines.append(style.paint(f"      Scenario: {scenario['name']}", DIM))
            lines += [f"        {step['keyword']} {step['text']}" for step in scenario["steps"]]
    if not payload["requirements"]:
        lines.append("  None.")
    if payload["pending"]:
        lines += ["", style.paint("Pending deltas from active changes", BOLD)]
        lines += [f"  {delta['change']}: {_delta_names(delta)}" for delta in payload["pending"]]
    if payload["history"]:
        lines += ["", style.paint("History", BOLD)]
        for entry in payload["history"]:
            lines.append(f"  {style.paint(entry['date'], DIM)}  {entry['change']}")
            lines += _indent(entry["outcome"] or "", "      ") if entry["outcome"] else []
    return "\n".join(lines)


def show_milestone(payload: Payload, style: Style) -> str:
    """A milestone with its roadmap, as text."""
    lines = [style.rule(f"Milestone: {payload['name']}")]
    bar = style.bar(payload["archived"], payload["total"])
    lines.append(f"  {bar} {payload['archived']}/{payload['total']} changes archived")
    for title, text in (payload["goal"] or {}).items():
        lines += _titled(title, text, style)
    lines += ["", style.paint("Roadmap", BOLD)]
    for line in payload["lines"]:
        mark = style.symbol("done") if line["status"] == "archived" else style.symbol("todo")
        status_text = style.paint(f"({line['status']})", DIM)
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
        lines += _titled(title, text, style)
    return "\n".join(lines)


_RENDERERS: dict[str, Callable[[Payload, Style], str]] = {
    "wm.status": status,
    "wm.inbox": inbox,
    "wm.check": check,
    "wm.ls": ls,
    "wm.show.change": show_change,
    "wm.show.spec": show_spec,
    "wm.show.milestone": show_milestone,
    "wm.show.exploration": show_exploration,
}


def to_text(payload: Payload, style: Style) -> str:
    """A payload as styled text, chosen by its schema."""
    return _RENDERERS[payload["schema"]](payload, style)

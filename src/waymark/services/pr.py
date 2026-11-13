"""Pull request text described from a change.

wm only writes the text. The links come from each repository's git remote as
this clone has it: nothing is fetched, and the pull request is opened by the
git host's own command-line tool, when the human asks. Links are built for
GitHub; on another host the text names the files and branches instead.
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from waymark.record import git
from waymark.record.changes import Change
from waymark.record.config import RECORD_DIR
from waymark.record.proposal import WHAT_CHANGES, WHY
from waymark.record.record import CHANGES, Record
from waymark.record.state import ChangeState, ItemState
from waymark.record.tasks import Item, RecordKind
from waymark.record.terms import Layout, ReviewLevel
from waymark.services.common import Refusal, find_change, repo_locations, state_of

PR_VERSION = 1

_REMOTES = (
    re.compile(r"^git@(?P<host>[^:]+):(?P<path>.+?)(?:\.git)?/?$"),
    re.compile(r"^ssh://(?:[^@/]+@)?(?P<host>[^/:]+)(?::\d+)?/(?P<path>.+?)(?:\.git)?/?$"),
    re.compile(r"^https?://(?:[^@/]+@)?(?P<host>[^/]+)/(?P<path>.+?)(?:\.git)?/?$"),
)
_HOSTS = frozenset({"github.com", "www.github.com"})


def web_url(remote: str | None) -> str | None:
    """A GitHub repository's web address from a remote URL; None for any other host."""
    for pattern in _REMOTES:
        match = pattern.match(remote or "")
        if match and match["host"].lower() in _HOSTS:
            return f"https://github.com/{match['path']}"
    return None


def _web(folder: Path | None) -> str | None:
    return web_url(git.remote_url(folder)) if folder is not None else None


def _review(item: Item, state: ItemState) -> str:
    if not item.ticked:
        return "not built yet"
    if state.level is ReviewLevel.NONE:
        return "no review needed"
    if not state.reviewed:
        return "not reviewed yet"
    verdicts = [r for r in item.records if r.kind is RecordKind.REVIEW and r.verdict]
    if verdicts:
        return f"independent review: {verdicts[-1].verdict.value if verdicts[-1].verdict else ''}"
    return "self-reviewed"


def _spec_lines(change: Change) -> list[str]:
    lines = []
    for domain, delta in sorted(change.deltas.items()):
        parts = [
            f"{label} {', '.join(r.name for r in requirements)}"
            for label, requirements in (
                ("adds", delta.added),
                ("modifies", delta.modified),
                ("removes", delta.removed),
            )
            if requirements
        ]
        lines.append(f"- {domain}: {'; '.join(parts) or 'its purpose or repos'}")
    return lines or ["No spec changes."]


def _places(record: Record, change: Change) -> dict[str, Path | None]:
    """The atlas and every code repo the change's items name, with their folders here."""
    config = record.config
    assert config is not None
    assert config.atlas_name is not None
    locations = repo_locations(record)
    touched = sorted(
        {item.repo for item in change.tasks.items if item.repo} if change.tasks else ()
    )
    places: dict[str, Path | None] = {config.atlas_name: record.project.root}
    for name in touched:
        location = locations.get(name)
        places[name] = location.folder if location else None
    return places


def _links(
    record: Record, name: str, places: dict[str, Path | None], here: str | None
) -> list[dict[str, str]]:
    """The change's proposal on its branch, and the other repos' pull requests from it."""
    record_web = _web(record.project.root)
    home = next(iter(places), None)
    links: list[dict[str, str]] = []
    if record_web:
        proposal = f"{RECORD_DIR}/{CHANGES}/{name}/proposal.md"
        links.append({"name": "change", "url": f"{record_web}/blob/{quote(name)}/{proposal}"})
    for other, folder in places.items():
        web = record_web if other == home else _web(folder)
        if other != here and web:
            query = quote(f"is:pr head:{name}", safe=":")
            links.append({"name": other, "url": f"{web}/pulls?q={query}"})
    return links


def _item_lines(change: Change, state: ChangeState, repo: str | None) -> list[str]:
    states = {item_state.number: item_state for item_state in state.items}
    lines = []
    for item in change.tasks.items if change.tasks else ():
        if repo is not None and item.repo != repo:
            continue
        mark = "x" if item.ticked else " "
        where = f", in {item.repo}" if item.repo and repo is None else ""
        review = _review(item, states[item.number])
        lines.append(f"- [{mark}] {item.number} {item.title} ({review}{where})")
    if not lines:
        return []
    return ["", f"## Items in {repo}" if repo else "## Items", "", *lines]


def _link_lines(
    name: str, places: dict[str, Path | None], here: str | None, links: list[dict[str, str]]
) -> list[str]:
    urls = {link["name"]: link["url"] for link in links}
    proposal = f"{RECORD_DIR}/{CHANGES}/{name}/proposal.md"
    home = next(iter(places), None)
    if "change" in urls:
        lines = [f"- The change: [{proposal}]({urls['change']})"]
    else:
        where = f' in the atlas "{home}"' if home else ""
        lines = [f"- The change: {proposal}{where}, on the branch {name}"]
    for other in places:
        if other != here:
            target = f"[{other}]({urls[other]})" if other in urls else other
            lines.append(f"- The pull request in {target}, from the branch {name}")
    return ["", "## Links", "", *lines]


def describe(record: Record, name: str, repo: str | None = None) -> dict[str, Any]:
    """The title and description of the pull request for a change, in one repository.

    In an atlas, ``repo`` names the code repo; without it the pull request is
    the atlas's own, which carries the record.
    """
    change = find_change(record, name)
    proposal = change.proposal
    if proposal is None:
        raise Refusal(f'The change "{name}" has no proposal yet, so there is nothing to describe.')
    atlas = record.layout is Layout.ATLAS
    if repo is not None and not atlas:
        raise Refusal("--repo names a code repo of an atlas; this project keeps everything in one.")
    places = _places(record, change) if atlas else {}
    code_repos = list(places)[1:]
    if repo is not None and repo not in code_repos:
        touched = ", ".join(code_repos) or "none"
        raise Refusal(f'The change "{name}" has no items in the repo "{repo}" (repos: {touched}).')
    here = repo or next(iter(places), None)
    links = _links(record, name, places, here)
    body = [proposal.sections.get(WHY, "").strip()]
    body += ["", f"## {WHAT_CHANGES}", "", proposal.sections.get(WHAT_CHANGES, "").strip()]
    body += ["", "## Specs", "", *_spec_lines(change)]
    body += _item_lines(change, state_of(record, change), repo)
    body += _link_lines(name, places, here, links)
    return {
        "schema": "wm.pr",
        "version": PR_VERSION,
        "change": name,
        "repo": repo,
        "branch": name,
        "title": proposal.title,
        "body": "\n".join(body).strip() + "\n",
        "links": links,
    }

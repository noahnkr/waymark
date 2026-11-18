"""Pull request text described from a change.

wm only writes the text. The links come from each repository's git remote as
this clone has it, and the proposal is linked at the checked-out commit so the
link outlives the branch: nothing is fetched, and the pull request is opened by the
git host's own command-line tool, when the human asks. Links are built for
GitHub; on another host the text names the files and branches instead.
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from waymark.record.artifacts.changes import Change
from waymark.record.artifacts.config import RECORD_DIR
from waymark.record.artifacts.proposal import WHAT_CHANGES, WHY
from waymark.record.evidence.records import RecordKind
from waymark.record.machine import git
from waymark.record.machine.branches import Branches
from waymark.record.record import Record
from waymark.record.state import review_state
from waymark.record.terms import Layout, ReviewLevel
from waymark.services.common import Refusal, find_active_or_archived, repo_locations

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


def _review_lines(record: Record, change: Change) -> list[str]:
    """The change's review: how it came out, then every review record with its findings.

    An override is said once, after the list.
    """
    review = review_state(change, record.default_review)
    records = change.tasks.review_records if change.tasks else ()
    last = records[-1] if records else None
    if review.level is ReviewLevel.NONE and review.reviewed:
        text = "No review needed (level none)."
    elif not review.reviewed:
        text = f"Not reviewed yet (level {review.level})."
    elif last is not None and last.kind is RecordKind.REVIEW and last.verdict:
        text = f"Independent review: {last.verdict.value}: {last.text}"
    elif last is not None:
        text = f"Self-reviewed: {last.text}"
    else:
        text = f"Reviewed (level {review.level})."
    lines = ["", "## Review", "", text]
    if change.tasks is not None:
        written = change.tasks.doc.lines
        shown = [record for record in change.tasks.log if record in records]
        if shown:
            lines.append("")
        for shown_record in shown:
            lines.append(written[shown_record.index].text.strip())
            lines += [f"  {written[f.index].text.strip()}" for f in shown_record.findings]
    override = change.tasks.latest(RecordKind.OVERRIDE) if change.tasks else None
    if override is not None:
        by = f" by {override.who}" if override.who else ""
        lines += ["", f"Archived without its review{by}: {override.text}"]
    return lines


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


def _proposal_path(change: Change) -> str:
    """The change's proposal from the top of the repository: active or archived."""
    return f"{RECORD_DIR}/{change.path}/proposal.md"


def _links(
    record: Record, change: Change, places: dict[str, Path | None], here: str | None
) -> list[dict[str, str]]:
    """The change's proposal, and the other repos' pull requests from its branch.

    The proposal is linked at the checked-out commit, which GitHub keeps after
    the branch is deleted; before the first commit, at the branch.
    """
    name = change.name
    record_web = _web(record.project.root)
    home = next(iter(places), None)
    links: list[dict[str, str]] = []
    if record_web:
        proposal = _proposal_path(change)
        ref = git.head_commit(record.project.root) or quote(name)
        links.append({"name": "change", "url": f"{record_web}/blob/{ref}/{proposal}"})
    for other, folder in places.items():
        web = record_web if other == home else _web(folder)
        if other != here and web:
            query = quote(f"is:pr head:{name}", safe=":")
            links.append({"name": other, "url": f"{web}/pulls?q={query}"})
    return links


def _item_lines(change: Change, repo: str | None) -> list[str]:
    lines = []
    for item in change.tasks.items if change.tasks else ():
        if repo is not None and item.repo != repo:
            continue
        mark = "x" if item.ticked else " "
        where = f" (in {item.repo})" if item.repo and repo is None else ""
        lines.append(f"- [{mark}] {item.number} {item.title}{where}")
    if not lines:
        return []
    return ["", f"## Items in {repo}" if repo else "## Items", "", *lines]


def _link_lines(
    change: Change, places: dict[str, Path | None], here: str | None, links: list[dict[str, str]]
) -> list[str]:
    name = change.name
    urls = {link["name"]: link["url"] for link in links}
    proposal = _proposal_path(change)
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
    change = find_active_or_archived(record, name)
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
    links = _links(record, change, places, here)
    body = [proposal.sections.get(WHY, "").strip()]
    body += ["", f"## {WHAT_CHANGES}", "", proposal.sections.get(WHAT_CHANGES, "").strip()]
    body += ["", "## Specs", "", *_spec_lines(change)]
    body += _item_lines(change, repo)
    if repo is None:
        body += _review_lines(record, change)
    if proposal.outcome:
        body += ["", "## Outcome", "", proposal.outcome.strip()]
    body += _link_lines(change, places, here, links)
    return {
        "schema": "wm.pr",
        "version": PR_VERSION,
        "change": name,
        "repo": repo,
        "branch": name,
        "base": Branches(record).of(change).base,
        "title": proposal.title,
        "body": "\n".join(body).strip() + "\n",
        "links": links,
    }

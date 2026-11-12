"""The acceptance fingerprint: a digest of everything an acceptance covers.

It covers what the human approved:

- the proposal, apart from the acceptance line and the outcome;
- every delta, and the design;
- each task item's definition (number, title, review level, criteria,
  verification and repo), but none of its evidence;
- the living text of what the deltas modify or remove, so that another change
  archiving into the same requirement withdraws this acceptance.

Line endings don't count, so two checkouts of one commit agree.
"""

import hashlib
from collections.abc import Mapping

from waymark.record.changes import Change
from waymark.record.specs import Spec
from waymark.record.terms import ReviewLevel

FINGERPRINT_LENGTH = 16
_ABSENT = "\x00absent"


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def fingerprint_parts(
    change: Change, specs: Mapping[str, Spec], default_review: ReviewLevel
) -> list[tuple[str, str]]:
    """The labeled pieces of text the fingerprint is made of, in a fixed order."""
    parts: list[tuple[str, str]] = []
    if change.proposal is not None:
        parts.append(("proposal", change.proposal.accepted_text()))
    if change.design is not None:
        parts.append(("design", change.design.doc.text))
    for domain in sorted(change.deltas):
        delta = change.deltas[domain]
        spec = specs.get(domain)
        parts.append((f"delta:{domain}", delta.doc.text))
        names = [item.name for item in delta.modified] + [item.name for item in delta.removed]
        for name in sorted(names):
            living = spec.requirement(name) if spec else None
            text = "\n".join(living.block) if living else _ABSENT
            parts.append((f"base:{domain}:{' '.join(name.split()).casefold()}", text))
        if delta.purpose is not None:
            parts.append((f"base-purpose:{domain}", spec.purpose if spec else _ABSENT))
        if delta.repos is not None:
            parts.append((f"base-repos:{domain}", ", ".join(spec.repos) if spec else _ABSENT))
    for item in change.tasks.items if change.tasks else ():
        definition = [
            item.title,
            item.level(default_review).value,
            item.criteria if item.criteria is not None else _ABSENT,
            item.verify if item.verify is not None else _ABSENT,
            item.repo if item.repo is not None else _ABSENT,
        ]
        parts.append((f"item:{item.number}", "\x00".join(definition)))
    return parts


def change_fingerprint(
    change: Change, specs: Mapping[str, Spec], default_review: ReviewLevel
) -> str:
    """The fingerprint of a change as it now stands."""
    digest = hashlib.sha256()
    for label, text in fingerprint_parts(change, specs, default_review):
        data = _normalized(text).encode("utf-8")
        digest.update(f"{label}\x00{len(data)}\x00".encode())
        digest.update(data)
    return digest.hexdigest()[:FINGERPRINT_LENGTH]

"""What wm gives the agents that build and review a change, beyond the record itself.

The severity rubric goes to every review, independent or self; the stopping rules go to the
implementer. Both live here so the context packs and the instructions give the same words.
"""

SEVERITY_RUBRIC = (
    "critical: a criterion or scenario doesn't hold, the code does what a requirement forbids, "
    "or a check fails.",
    "warning: everything holds, but an edge is untested, a requirement is met only by accident, "
    "or a likely next change would break it.",
    "suggestion: clarity, naming or duplication that no user would notice.",
    "When a finding could be either of two severities, it takes the higher, and every critical "
    "finding names the item to rebuild.",
)
"""How a review grades its findings."""

STOPPING_RULES = (
    "The record leaves a choice open, or two parts of it disagree: stop and end with spec-gap, "
    "naming what is missing.",
    "A check fails for a reason outside the item, or the item needs a file or repo outside its "
    "scope: stop and end with blocked, naming the cause.",
    "The same check still fails after three attempts at it: stop and end with partial, saying "
    "what was tried.",
    "Other work turns up that the item doesn't ask for: leave it undone, name it in a note, and "
    "finish the item as asked.",
)
"""When an implementer stops, and the result it ends with."""


def human_items_note(numbers: tuple[str, ...]) -> str | None:
    """What a review takes as given for the items the human did; None when there are none."""
    if not numbers:
        return None
    named = f"Item {numbers[0]} was" if len(numbers) == 1 else f"Items {', '.join(numbers)} were"
    its = "its tick is" if len(numbers) == 1 else "their ticks are"
    return (
        f"{named} done by the human: {its} the human's confirmation of what only they could "
        "check, so take that as given. Still check anything they left in the repo, such as a "
        "resource they updated."
    )

"""The skills and agent definitions wm installs into a project.

They are written once, tool-neutral: they use only what every agent tool has,
which is reading and editing files, running commands and calling ``wm``.
Adapters copy them into each tool's folders.
"""

from importlib import resources

SKILLS = (
    "wm-kickoff",
    "wm-explore",
    "wm-propose",
    "wm-update",
    "wm-apply",
    "wm-archive",
    "wm-onboard",
    "wm-pr",
)
"""Every skill, by the name it is installed under."""

IMPLEMENTER = "wm-implementer"
REVIEWER = "wm-reviewer"
AGENTS = (IMPLEMENTER, REVIEWER)
"""The agents a change's items are delegated to."""

SKILL_FILE = "SKILL.md"


def skill(name: str) -> str:
    """A skill's file, as it is installed."""
    source = resources.files("waymark.assets").joinpath("skills", name, SKILL_FILE)
    return source.read_text(encoding="utf-8")


def agent(name: str) -> tuple[str, str]:
    """An agent definition: its one-line description, and its instructions."""
    source = resources.files("waymark.assets").joinpath("agents", f"{name}.md")
    text = source.read_text(encoding="utf-8")
    _, header, body = text.split("---\n", 2)
    fields = dict(line.split(": ", 1) for line in header.strip().split("\n"))
    assert fields["name"] == name
    return fields["description"], body.lstrip("\n")

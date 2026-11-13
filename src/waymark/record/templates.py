"""The built-in templates. A project contains no template files; wm carries them."""

from importlib import resources

CONFIG = "config.toml"
ATLAS_CONFIG = "config-atlas.toml"
CHARTER = "charter.md"
PROPOSAL = "proposal.md"
GOAL = "goal.md"
ROADMAP = "roadmap.md"
EXPLORATION = "exploration.md"
DELTA = "delta.md"
DESIGN = "design.md"
TASKS = "tasks.md"
CI_WORKFLOW = "ci-workflow.yml"


def render(name: str, **values: str) -> str:
    """A template's text with its ``{{placeholders}}`` filled in."""
    source = resources.files("waymark.record").joinpath("templates", name)
    text = source.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    assert "{{" not in text, f"template {name} has an unfilled placeholder"
    return text


def title_from_name(name: str) -> str:
    """A readable title for a kebab-case name."""
    return name.replace("-", " ").capitalize()

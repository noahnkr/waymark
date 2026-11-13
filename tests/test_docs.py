"""The docs: generated references are current, required docs exist, and the release checks."""

import re
from pathlib import Path

import pytest

from tools import docs, release

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = (
    "Record",
    "Charter",
    "Spec",
    "Requirement",
    "Scenario",
    "Atlas",
    "Change",
    "Proposal",
    "Delta",
    "Design",
    "Task item",
    "Acceptance",
    "Short path",
    "Conflict",
    "Sync",
    "Archive",
    "Owner",
    "Exploration",
    "Milestone",
    "Planner",
    "Implementer",
    "Reviewer",
    "Review level",
    "Context pack",
    "Spec gap",
)
REQUIRED = (
    "README.md",
    "CHANGELOG.md",
    "docs/getting-started.md",
    "docs/concepts.md",
    "docs/multi-repo.md",
    "docs/cli.md",
    "docs/json.md",
    "docs/architecture.md",
    "docs/smoke-test.md",
    "docs/assets/banner.svg",
)


def test_generated_references_and_readme_evidence_are_current() -> None:
    """CI fails when the CLI reference, the JSON reference or the README's evidence drift."""
    assert docs.stale() == []


def test_every_required_doc_exists() -> None:
    for relative in REQUIRED:
        assert (ROOT / relative).is_file(), relative


def test_the_cli_reference_covers_every_command() -> None:
    text = (ROOT / "docs/cli.md").read_text(encoding="utf-8")
    for command in ("init", "atlas register", "atlas doctor", "run-hook", "pr", "context"):
        assert f"## wm {command}\n" in text, command


def test_the_glossary_defines_every_term() -> None:
    text = (ROOT / "docs/concepts.md").read_text(encoding="utf-8")
    for term in GLOSSARY:
        assert re.search(rf"^\| \*\*{re.escape(term)}\*\* \|", text, re.MULTILINE), term


def test_doc_links_lead_to_files_that_exist() -> None:
    for path in [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#:]+)(?:#[^)]*)?\)", text):
            assert (path.parent / target).exists(), f"{path.name} links to {target}"


CHANGELOG = """# Changelog

## [0.2.0] - 2027-01-02

Later.

## [0.1.0] - 2026-11-20

First release.

Smoke test: passed on 2026-11-19.
"""


def test_release_is_ready_when_tag_version_changelog_and_smoke_test_agree() -> None:
    assert release.problems("v0.1.0", "0.1.0", CHANGELOG, "verified: 2.1.400") == []
    assert release.entry(CHANGELOG, "0.1.0") == (
        "## [0.1.0] - 2026-11-20\n\nFirst release.\n\nSmoke test: passed on 2026-11-19.\n"
    )


@pytest.mark.parametrize(
    ("tag", "version", "changelog", "readme", "problem"),
    [
        ("v0.1.1", "0.1.0", CHANGELOG, "", "doesn't match"),
        ("v0.1.0.dev0", "0.1.0.dev0", CHANGELOG, "", "development version"),
        ("v0.3.0", "0.3.0", CHANGELOG, "", "has no"),
        ("v0.1.0", "0.1.0", CHANGELOG.replace("2026-11-20", "unreleased"), "", "no release date"),
        ("v0.1.0", "0.1.0", CHANGELOG.replace("Smoke test", "Tested"), "", "smoke test result"),
        ("v0.1.0", "0.1.0", CHANGELOG, release.PENDING, "still says"),
    ],
)
def test_release_is_refused_until_everything_is_ready(
    tag: str, version: str, changelog: str, readme: str, problem: str
) -> None:
    assert any(problem in found for found in release.problems(tag, version, changelog, readme))

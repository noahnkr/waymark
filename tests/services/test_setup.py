"""Setting up a project and creating artifacts from the built-in templates."""

import datetime
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import git_init
from tests.support import Workspace, document
from waymark import __version__, adapters
from waymark.record.artifacts.charter import parse_charter
from waymark.record.artifacts.deltas import parse_delta
from waymark.record.artifacts.design import parse_design
from waymark.record.artifacts.explorations import parse_exploration
from waymark.record.artifacts.proposal import parse_proposal
from waymark.record.artifacts.tasks import parse_tasks
from waymark.record.machine.files import RecordFiles
from waymark.record.machine.project import find_project
from waymark.record.markdown.text import Document
from waymark.record.record import load_record
from waymark.record.state import ExplorationStatus, StepKind, derive_state
from waymark.record.terms import Layout, Phase
from waymark.record.writing import ignore, templates
from waymark.record.writing.layout import _comment_flags
from waymark.services import check, ci, integration, lifecycle, setup
from waymark.services.common import Refusal

TODAY = datetime.date(2026, 1, 15)


def test_init_refuses_outside_a_git_repository(tmp_path: Path) -> None:
    with pytest.raises(Refusal, match="git init"):
        setup.init_project(tmp_path)
    assert not (tmp_path / "waymark").exists()


def test_init_creates_the_settings_and_a_charter_skeleton(tmp_path: Path) -> None:
    git_init(tmp_path)
    done = setup.init_project(tmp_path)
    assert {"waymark/charter.md", "waymark/config.toml"} <= set(done.paths)
    assert "wm-kickoff" in done.message
    record = load_record(find_project(tmp_path))
    assert record.problems == ()
    assert record.config is not None
    assert record.config.wm_version == __version__
    assert record.config.record_format == 1
    assert record.layout is Layout.REPO
    assert record.charter is not None
    assert record.charter.title == tmp_path.name


def test_init_pins_the_version_that_created_the_project(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    text = (tmp_path / "waymark" / "config.toml").read_text(encoding="utf-8")
    assert f'wm_version = "{__version__}"' in text


def test_init_as_an_atlas_names_the_atlas(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path, atlas="suite")
    record = load_record(find_project(tmp_path))
    assert record.problems == ()
    assert record.layout is Layout.ATLAS
    assert record.config is not None
    assert record.config.atlas_name == "suite"
    other = tmp_path / "other"
    git_init(other)
    with pytest.raises(Refusal, match="atlas name"):
        setup.init_project(other, atlas="not a name")
    assert not (other / "waymark").exists()


def test_init_puts_the_record_at_the_top_of_the_repository(tmp_path: Path) -> None:
    git_init(tmp_path)
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    setup.init_project(nested)
    assert (tmp_path / "waymark" / "config.toml").is_file()
    assert not (nested / "waymark").exists()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8")


def git_settings(root: Path) -> str:
    """This clone's own git settings, as git lists them."""
    return git(root, "config", "--local", "--list")


def hooks_path(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--local", "core.hooksPath"],
        capture_output=True,
        check=False,
    )
    return result.stdout.decode("utf-8").strip() or None


def record_bytes(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in (root / "waymark").rglob("*")
        if path.is_file()
    }


def test_init_writes_the_block_and_leaves_only_the_record_and_gitignore_to_commit(
    tmp_path: Path,
) -> None:
    """Scenario: New project."""
    git_init(tmp_path)
    settings = git_settings(tmp_path)
    done = setup.init_project(tmp_path)
    assert git_settings(tmp_path) == settings
    assert not (tmp_path / ".waymark").exists()
    patterns = integration.ignore_patterns(adapters.names())
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == ignore.render(patterns)
    assert ".gitignore" in done.paths
    new = git(tmp_path, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert new
    assert all(line.startswith("?? ") for line in new)
    paths = {line[3:] for line in new}
    assert ".gitignore" in paths
    assert all(path == ".gitignore" or path.startswith("waymark/") for path in paths), paths
    assert staged(tmp_path) == []


def cloned_project(tmp_path: Path) -> Path:
    """A project whose record and .gitignore are committed, cloned afresh."""
    origin = tmp_path / "origin"
    git_init(origin)
    git(origin, "config", "user.email", "sam@example.com")
    setup.init_project(origin)
    git(origin, "add", "-A")
    git(origin, "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "chore: start")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", str(origin), str(clone)], check=True, capture_output=True
    )
    return clone


RECORD_FOLDERS = (
    "specs",
    "changes",
    "changes/archive",
    "explorations",
    "explorations/archive",
    "milestones",
    "milestones/archive",
    "resources",
)


def test_init_keeps_every_record_folder_in_git(tmp_path: Path) -> None:
    """Scenario: New record."""
    origin = tmp_path / "origin"
    git_init(origin)
    done = setup.init_project(origin)
    for folder in RECORD_FOLDERS:
        keep = origin / "waymark" / folder / ".gitkeep"
        assert keep.read_bytes() == b"", folder
        assert f"waymark/{folder}/.gitkeep" in done.paths
    assert load_record(find_project(origin)).problems == ()

    clone = cloned_project(tmp_path)
    for folder in RECORD_FOLDERS:
        assert (clone / "waymark" / folder).is_dir(), folder


def test_init_in_a_fresh_clone_sets_up_this_machine_and_leaves_the_record_alone(
    tmp_path: Path,
) -> None:
    """Scenario: Fresh clone."""
    clone = cloned_project(tmp_path)
    assert not (clone / ".claude").exists()
    assert not (clone / ".waymark").exists()
    record_before = record_bytes(clone)
    gitignore_before = (clone / ".gitignore").read_bytes()
    settings = git_settings(clone)

    done = setup.init_project(clone)

    assert "This machine is set up" in done.message
    assert "commit them" not in done.message
    assert all(
        (clone / path).is_file()
        for path in integration.integration_files(RecordFiles(clone), adapters.names())
    )
    assert git_settings(clone) == settings
    assert not (clone / ".waymark").exists()
    assert "git hooks" not in done.message
    assert (clone / ".gitignore").read_bytes() == gitignore_before
    assert record_bytes(clone) == record_before
    assert git(clone, "status", "--porcelain", "--untracked-files=all") == ""


def test_init_in_a_clone_adds_the_block_when_gitignore_lacks_it(tmp_path: Path) -> None:
    clone = cloned_project(tmp_path)
    (clone / ".gitignore").unlink()
    record_before = record_bytes(clone)
    done = setup.init_project(clone)
    assert "created: .gitignore" in done.message
    assert ".gitignore" in done.paths
    patterns = integration.ignore_patterns(adapters.names())
    assert (clone / ".gitignore").read_text(encoding="utf-8") == ignore.render(patterns)
    assert record_bytes(clone) == record_before


def test_init_run_again_changes_nothing_and_says_so(tmp_path: Path) -> None:
    """Scenario: Run again."""
    clone = cloned_project(tmp_path)
    setup.init_project(clone)
    before = {
        path: path.read_bytes()
        for path in clone.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    done = setup.init_project(clone)
    after = {
        path: path.read_bytes()
        for path in clone.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert after == before
    assert done.message == "This machine is already set up. Nothing changed."
    assert done.paths == ()


def test_init_in_a_clone_is_refused_on_another_pinned_version(tmp_path: Path) -> None:
    """Scenario: Other version."""
    clone = cloned_project(tmp_path)
    config = clone / "waymark" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            f'wm_version = "{__version__}"', 'wm_version = "9.9.9"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(Refusal) as refusal:
        setup.init_project(clone)
    assert "pinned to wm 9.9.9" in str(refusal.value)
    assert "waymark-cli==9.9.9" in str(refusal.value)
    assert not (clone / ".claude").exists()
    assert not (clone / ".agents").exists()
    assert not (clone / ".waymark").exists()


def test_scenario_record_in_another_format(tmp_path: Path) -> None:
    """Scenario: Record in another format, for wm init in a clone."""
    clone = cloned_project(tmp_path)
    config = clone / "waymark/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("record_format = 1", "record_format = 3"),
        encoding="utf-8",
    )
    with pytest.raises(Refusal, match="Install the wm version that wrote it") as refusal:
        setup.init_project(clone)
    assert "format 3" in str(refusal.value)
    assert not (clone / ".claude").exists()
    assert not (clone / ".agents").exists()
    assert not (clone / ".waymark").exists()


def test_init_with_a_record_refuses_options_that_only_apply_to_a_new_one(tmp_path: Path) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    before = record_bytes(tmp_path)
    with pytest.raises(Refusal, match="already has a record"):
        setup.init_project(tmp_path, tools=("claude-code",))
    with pytest.raises(Refusal, match="already has a record"):
        setup.init_project(tmp_path, atlas="suite")
    assert record_bytes(tmp_path) == before


def code_repo_files(root: Path) -> dict[Path, bytes]:
    """Every file in a repository outside .git, with its bytes."""
    return {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


@pytest.mark.parametrize(
    ("pointer_file", "pointer_text"),
    [
        (
            "waymark/config.toml",
            '[pointer]\natlas = "notes"\npath = "../notes-atlas"\nwm_version = "0.1.1"\n',
        ),
    ],
    ids=["pointer"],
)
@pytest.mark.parametrize(
    "options",
    [{}, {"atlas": "suite"}, {"tools": ("claude-code",)}],
    ids=["plain", "with --atlas", "with --tool"],
)
def test_init_in_a_code_repo_is_refused_and_writes_nothing(
    tmp_path: Path, pointer_file: str, pointer_text: str, options: dict[str, object]
) -> None:
    """Scenario: Init in a code repo."""
    repo = tmp_path / "notes-api"
    git_init(repo)
    (repo / pointer_file).parent.mkdir(parents=True)
    (repo / pointer_file).write_text(pointer_text, encoding="utf-8")
    before = code_repo_files(repo)

    with pytest.raises(Refusal) as refusal:
        setup.init_project(repo, **options)  # type: ignore[arg-type]

    message = str(refusal.value)
    assert '"notes"' in message
    assert 'Run "wm init" in the atlas' in message
    assert code_repo_files(repo) == before
    hooks_path = subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath"], capture_output=True, check=False
    )
    assert hooks_path.stdout == b""


def test_ignore_patterns_list_the_shared_skills_and_each_tool_and_not_the_hooks() -> None:
    tools = adapters.names()
    expected = ["/.agents/skills/wm-*/"]
    for tool in tools:
        expected += adapters.get(tool).ignored
    assert integration.ignore_patterns(tools) == expected
    assert integration.ignore_patterns(()) == ["/.agents/skills/wm-*/"]
    assert not any(".waymark" in pattern for pattern in expected)


def test_ignore_patterns_refuse_a_tool_wm_does_not_know() -> None:
    with pytest.raises(Refusal, match="not an agent tool"):
        integration.ignore_patterns(("no-such-tool",))


def ignored_by_git(root: Path, patterns: list[str], paths: list[str]) -> set[str]:
    """The paths that git ignores in a fresh repository whose .gitignore holds the patterns."""
    git_init(root)
    (root / ".gitignore").write_text("".join(f"{line}\n" for line in patterns), encoding="utf-8")
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", "--stdin"],
        input="".join(f"{path}\n" for path in paths).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return set(result.stdout.decode("utf-8").splitlines())


def test_every_file_wm_writes_for_a_machine_is_ignored(tmp_path: Path) -> None:
    tools = adapters.names()
    paths = sorted(integration.integration_files(RecordFiles(tmp_path), tools))
    assert paths
    root = tmp_path / "repo"
    ignored = ignored_by_git(root, integration.ignore_patterns(tools), paths)
    assert ignored == set(paths)


def test_the_patterns_leave_the_projects_own_files_alone(tmp_path: Path) -> None:
    own = [
        "waymark/config.toml",
        ".waymark/atlas.toml",
        ".gitignore",
        ".claude/skills/team-skill/SKILL.md",
        ".claude/agents/helper.md",
        ".agents/skills/team-skill/SKILL.md",
        "docs/.claude/settings.json",
    ]
    patterns = integration.ignore_patterns(adapters.names())
    assert ignored_by_git(tmp_path / "repo", patterns, own) == set()


def staged(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--name-only"],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8").splitlines()


def test_setup_machine_writes_the_machine_files_and_the_block_and_no_hooks(
    tmp_path: Path,
) -> None:
    git_init(tmp_path)
    setup.init_project(tmp_path)
    (tmp_path / ".gitignore").unlink(missing_ok=True)
    (tmp_path / ".claude/skills/wm-apply/SKILL.md").unlink()
    settings = git_settings(tmp_path)
    record_before = {
        path: path.read_bytes() for path in (tmp_path / "waymark").rglob("*") if path.is_file()
    }

    machine = integration.setup_machine(load_record(find_project(tmp_path)))

    statuses = {change.path: change.status for change in machine.changes}
    assert statuses[".claude/skills/wm-apply/SKILL.md"] == "created"
    assert statuses[".gitignore"] == "created"
    assert set(machine.paths) == {".claude/skills/wm-apply/SKILL.md", ".gitignore"}
    patterns = integration.ignore_patterns(adapters.names()[:1])
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == ignore.render(patterns)
    assert git_settings(tmp_path) == settings
    assert not (tmp_path / ".waymark").exists()
    record_after = {
        path: path.read_bytes() for path in (tmp_path / "waymark").rglob("*") if path.is_file()
    }
    assert record_after == record_before
    assert staged(tmp_path) == []


def initialized_with_block(root: Path) -> Path:
    git_init(root)
    setup.init_project(root)
    return root


def test_update_leaves_a_current_block_alone(tmp_path: Path) -> None:
    """Scenario: Block already current."""
    root = initialized_with_block(tmp_path)
    gitignore = root / ".gitignore"
    before = gitignore.read_bytes()
    done = integration.update(root)
    assert gitignore.read_bytes() == before
    assert ".gitignore" not in done.message
    assert done.message == "Everything is up to date."


def test_update_replaces_an_out_of_date_block_in_place(tmp_path: Path) -> None:
    """Scenario: Block out of date."""
    root = initialized_with_block(tmp_path)
    gitignore = root / ".gitignore"
    crlf = "\r\n"
    stale = ignore.render(["/.agents/skills/wm-*/", "/.old-tool/", "/.waymark/hooks/"], crlf)
    around = ("# ours" + crlf + "build/" + crlf + crlf, crlf + "*.log" + crlf)
    gitignore.write_bytes((around[0] + stale + around[1]).encode("utf-8"))

    done = integration.update(root)

    patterns = integration.ignore_patterns(adapters.names()[:1])
    current = ignore.render(patterns, crlf)
    assert gitignore.read_bytes() == (around[0] + current + around[1]).encode("utf-8")
    assert "updated: .gitignore" in done.message
    assert done.message.splitlines()[-1] == "Review the changes to .gitignore and commit them."
    assert ".gitignore" in done.paths


def test_update_that_changes_only_machine_files_asks_for_no_commit(tmp_path: Path) -> None:
    """Scenario: Update changes only machine files."""
    root = initialized_with_block(tmp_path)
    (root / ".claude/skills/wm-apply/SKILL.md").write_text("edited by hand\n", encoding="utf-8")
    (root / ".agents/skills/wm-pr/SKILL.md").unlink()

    done = integration.update(root)

    assert "updated: .claude/skills/wm-apply/SKILL.md" in done.message
    assert "created: .agents/skills/wm-pr/SKILL.md" in done.message
    assert done.message.splitlines()[-1] == "Updated this machine's files."
    assert "commit" not in done.message.lower()
    assert staged(root) == []


def test_update_names_the_record_and_the_workflow_when_they_change(tmp_path: Path) -> None:
    root = initialized_with_block(tmp_path)
    workflow = root / ci.WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text("old\n", encoding="utf-8")
    (root / "waymark/specs/.gitkeep").unlink()
    done = integration.update(root)
    assert done.message.splitlines()[-1] == (
        f"Review the changes to waymark/ and {ci.WORKFLOW} and commit them."
    )


def test_new_change_writes_a_proposal_owned_by_the_git_user(project: Workspace) -> None:
    done = setup.create_change(project.root, "add-limit")
    assert done.paths == ("changes/add-limit/proposal.md",)
    change = project.record().changes["add-limit"]
    assert change.proposal is not None
    assert change.proposal.owner == "Sam Doe"
    assert change.proposal.title == "Add limit"
    assert not change.short_path
    state = project.change_state()
    assert (state.phase, state.next_step.kind) == (Phase.PROPOSED, StepKind.PROPOSE)


def test_scenario_new_proposal(project: Workspace) -> None:
    """Requirement "Template examples": a good and a bad example, and no problem from them."""
    setup.create_change(project.root, "add-limit")
    text = project.read("changes/add-limit/proposal.md")
    assert "Good: " in text
    assert "Bad: " in text
    change = project.record().changes["add-limit"]
    assert {p.code for p in change.problems} == {"empty-section"}


@pytest.mark.parametrize(
    ("template", "path", "parse"),
    [
        ("proposal.md", "changes/x/proposal.md", parse_proposal),
        ("design.md", "changes/x/design.md", parse_design),
        ("tasks.md", "changes/x/tasks.md", parse_tasks),
        ("delta.md", "changes/x/specs/search.md", lambda doc: parse_delta("search", doc)),
        ("charter.md", "charter.md", parse_charter),
        ("exploration.md", "explorations/x.md", lambda doc: parse_exploration("x", doc)),
    ],
)
def test_every_template_carries_examples_the_checks_ignore(
    template: str, path: str, parse: Callable[[Document], Any]
) -> None:
    text = templates.render(template, title="X", facts="- Owner: Sam Doe\n")
    assert "Good" in text
    assert "Bad" in text
    doc = document(text, path)
    commented = {
        index + 1
        for index, flag in enumerate(_comment_flags(doc))
        if flag
        and doc.lines[index].text.strip()
        and not doc.lines[index].text.lstrip().startswith("<!--")
    }
    assert [p for p in parse(doc).problems if p.line in commented] == []


def test_new_change_can_name_another_owner_and_take_the_short_path(project: Workspace) -> None:
    setup.create_change(project.root, "fix-typo", short=True, owner="Robin Roe")
    change = project.record().changes["fix-typo"]
    assert change.proposal is not None
    assert change.proposal.owner == "Robin Roe"
    assert change.short_path


def test_new_change_needs_an_owner(workspace: Workspace) -> None:
    git_init(workspace.root, name=None)
    with pytest.raises(Refusal, match="--owner"):
        setup.create_change(workspace.root, "add-limit")
    assert workspace.record().changes == {}


@pytest.mark.parametrize("name", ["Add-Limit", "add_limit", "add-limit-2", ""])
def test_new_change_refuses_a_name_that_breaks_the_naming_rule(
    project: Workspace, name: str
) -> None:
    with pytest.raises(Refusal, match="lowercase words"):
        setup.create_change(project.root, name)


def test_new_change_refuses_a_name_already_in_use(project: Workspace) -> None:
    setup.create_change(project.root, "add-limit")
    with pytest.raises(Refusal, match="already is a change"):
        setup.create_change(project.root, "add-limit")


def test_scenario_new_milestone(project: Workspace) -> None:
    done = setup.create_milestone(project.root, "faster-search")
    assert done.paths == ("milestones/faster-search/milestone.md",)
    assert sorted(p.name for p in project.path("milestones/faster-search").iterdir()) == [
        "milestone.md"
    ]
    text = project.read("milestones/faster-search/milestone.md")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == ["## Goal", "## Done when", "## Non-goals", "## Roadmap"]
    record = project.record()
    milestone = record.milestones["faster-search"]
    assert milestone.goal is not None
    assert milestone.roadmap is not None
    assert milestone.roadmap.entries == ()
    assert check.check_record(record, datetime.datetime.now(datetime.UTC)) != ()
    with pytest.raises(Refusal, match="already is a milestone"):
        setup.create_milestone(project.root, "faster-search")


def test_new_exploration_starts_open(project: Workspace) -> None:
    setup.create_exploration(project.root, "paging")
    record = project.record()
    assert record.problems == ()
    assert derive_state(record).explorations["paging"].status is ExplorationStatus.OPEN
    with pytest.raises(Refusal, match="already is an exploration"):
        setup.create_exploration(project.root, "paging")


def status_line(project: Workspace, name: str) -> str:
    return next(
        line
        for line in project.read(f"explorations/{name}.md").splitlines()
        if line.startswith("- Status:")
    )


def test_scenario_change_from_an_open_exploration(project: Workspace) -> None:
    setup.create_exploration(project.root, "result-paging")
    before = project.read("explorations/result-paging.md")
    done = setup.create_change(project.root, "add-search-limit", source="result-paging")
    assert project.read("changes/add-search-limit/proposal.md")
    assert status_line(project, "result-paging") == (
        "- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md)"
    )
    after = project.read("explorations/result-paging.md")
    assert [a for a, b in zip(before.splitlines(), after.splitlines(), strict=True) if a != b] == [
        "- Status: open"
    ]
    assert "result-paging" in done.message
    record = project.record()
    assert [p for p in record.problems if p.path.startswith("explorations/")] == []
    state = derive_state(record).explorations["result-paging"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, "change add-search-limit")


def test_scenario_a_second_change_from_the_same_exploration(project: Workspace) -> None:
    setup.create_exploration(project.root, "result-paging")
    setup.create_change(project.root, "add-search-limit", source="result-paging")
    setup.create_change(project.root, "add-page-cursor", source="result-paging")
    assert status_line(project, "result-paging") == (
        "- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md), "
        "[add-page-cursor](../changes/add-page-cursor/proposal.md)"
    )
    problems = project.record().problems
    assert [p for p in problems if p.path.startswith("explorations/")] == []


def test_scenario_milestone_from_an_exploration(project: Workspace) -> None:
    setup.create_exploration(project.root, "faster-search-ideas")
    setup.create_milestone(project.root, "faster-search", "faster-search-ideas")
    assert status_line(project, "faster-search-ideas") == (
        "- Status: led-to [faster-search](../milestones/faster-search/milestone.md)"
    )
    state = derive_state(project.record()).explorations["faster-search-ideas"]
    assert (state.status, state.detail) == (ExplorationStatus.LED_TO, "milestone faster-search")


def test_scenario_unknown_exploration(project: Workspace) -> None:
    with pytest.raises(Refusal, match="result-paging"):
        setup.create_change(project.root, "add-search-limit", source="result-paging")
    assert not project.path("changes/add-search-limit").exists()
    project.write("explorations/archive/2026-11-01-result-paging.md", "# Result paging\n")
    with pytest.raises(Refusal, match="result-paging"):
        setup.create_milestone(project.root, "faster-search", "result-paging")
    assert not project.path("milestones/faster-search").exists()


def test_writes_are_refused_when_the_pinned_version_differs(project: Workspace) -> None:
    project.change()
    project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    attempts: tuple[Callable[[], object], ...] = (
        lambda: setup.create_change(project.root, "add-order"),
        lambda: setup.create_exploration(project.root, "paging"),
        lambda: lifecycle.accept(project.root, "add-limit", TODAY),
        lambda: lifecycle.tick(project.root, "add-limit", "1.1"),
        lambda: lifecycle.archive(project.root, "add-limit", TODAY, built="Done."),
    )
    for attempt in attempts:
        with pytest.raises(Refusal) as refusal:
            attempt()
        assert "pinned to wm 9.9.9" in str(refusal.value)
        assert "waymark-cli==9.9.9" in str(refusal.value)
    assert list(project.record().changes) == ["add-limit"]


def test_reads_still_work_when_the_pinned_version_differs(project: Workspace) -> None:
    project.change()
    project.replace("config.toml", f'wm_version = "{__version__}"', 'wm_version = "9.9.9"')
    findings = check.check(project.root, datetime.datetime.now(datetime.UTC))
    assert [finding.code for finding in findings] == ["version-pin"]
    assert not check.has_errors(findings)


def test_writes_are_refused_when_the_record_format_differs(project: Workspace) -> None:
    project.replace("config.toml", "record_format = 1", "record_format = 2")
    with pytest.raises(Refusal, match="this wm reads only format 1"):
        setup.create_change(project.root, "add-limit")


def test_writes_are_refused_when_the_settings_are_broken(project: Workspace) -> None:
    project.replace("config.toml", 'default_review = "self"', 'default_review = "strict"')
    with pytest.raises(Refusal, match=r"config\.toml has problems"):
        setup.create_change(project.root, "add-limit")


def test_commands_outside_a_project_say_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(Refusal, match="initialize"):
        setup.create_change(tmp_path, "add-limit")


OLD_HOOKS_DIR = ".waymark/hooks"


def install_old_hooks(root: Path) -> None:
    """The git hooks as wm 0.1.1 left them in a clone: two scripts, and core.hooksPath."""
    folder = root / OLD_HOOKS_DIR
    folder.mkdir(parents=True)
    for name in ("commit-msg", "pre-commit"):
        (folder / name).write_text(f"#!/bin/sh\nwm run-hook {name}\n", encoding="utf-8")
    (folder / ".gitattributes").write_text("* text eol=lf\n", encoding="utf-8")
    git(root, "config", "core.hooksPath", OLD_HOOKS_DIR)


def waymark_folder(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in (root / ".waymark").rglob("*")
        if path.is_file()
    }


def test_update_leaves_the_git_hooks_wm_0_1_1_installed_alone(tmp_path: Path) -> None:
    """Nothing cleans up 0.1.1's hooks: the clone's owner removes them by hand."""
    root = initialized_with_block(tmp_path)
    install_old_hooks(root)
    settings = git_settings(root)
    before = waymark_folder(root)

    done = integration.update(root)

    assert git_settings(root) == settings
    assert hooks_path(root) == OLD_HOOKS_DIR
    assert waymark_folder(root) == before
    assert "hooks" not in done.message
    assert done.message == "Everything is up to date."


def test_init_in_a_clone_leaves_the_git_hooks_wm_0_1_1_installed_alone(tmp_path: Path) -> None:
    clone = cloned_project(tmp_path)
    setup.init_project(clone)
    install_old_hooks(clone)
    settings = git_settings(clone)
    before = waymark_folder(clone)

    done = setup.init_project(clone)

    assert git_settings(clone) == settings
    assert waymark_folder(clone) == before
    assert done.message == "This machine is already set up. Nothing changed."


@pytest.mark.parametrize("value", [".husky", ".waymark/hooks-mine", ".githooks"])
def test_init_leaves_another_hook_setup_alone(tmp_path: Path, value: str) -> None:
    """A clone's own hook setup is never touched."""
    clone = cloned_project(tmp_path)
    setup.init_project(clone)
    folder = clone / value
    folder.mkdir(parents=True)
    (folder / "pre-commit").write_text("#!/bin/sh\nnpx lint-staged\n", encoding="utf-8")
    git(clone, "config", "core.hooksPath", value)
    before = (folder / "pre-commit").read_bytes()

    done = setup.init_project(clone)

    assert hooks_path(clone) == value
    assert (folder / "pre-commit").read_bytes() == before
    assert sorted(path.name for path in folder.iterdir()) == ["pre-commit"]
    assert done.message == "This machine is already set up. Nothing changed."


LAYOUT_CODES = {
    "layout",
    "missing-owner",
    "glossary-format",
    "unknown-status",
    "unexpected-text",
    "malformed-item",
}


def test_every_template_is_written_in_the_current_layouts(tmp_path: Path) -> None:
    """Each template, filled in as wm fills it, has no layout problem."""
    git_init(tmp_path)
    setup.init_project(tmp_path)
    setup.create_change(tmp_path, "add-limit", short=True)
    setup.create_exploration(tmp_path, "paging")
    setup.create_milestone(tmp_path, "faster-search")
    change = tmp_path / "waymark" / "changes" / "add-limit"
    (change / "specs").mkdir()
    for path, name in [
        (change / "tasks.md", templates.TASKS),
        (change / "design.md", templates.DESIGN),
        (change / "specs" / "search.md", templates.DELTA),
    ]:
        path.write_text(templates.render(name), encoding="utf-8")
    record = load_record(find_project(tmp_path))
    assert {p.code for p in record.problems} & LAYOUT_CODES == set()
    tasks = record.changes["add-limit"].tasks
    assert tasks is not None
    assert tasks.items[1].delegate
    criteria = tasks.items[1].criteria or ""
    bullets = [line for line in criteria.splitlines() if line.startswith("- ")]
    assert len(bullets) == 2
    assert record.explorations["paging"].status == "open"
    charter = (tmp_path / "waymark" / "charter.md").read_text(encoding="utf-8")
    assert "## Rules\n" in charter
    assert "### Apply\n" not in charter


MILESTONE_FILE = "milestones/faster-search/milestone.md"


def faster_search(roadmap: str, *, newline: str = "\n") -> str:
    text = (
        "# Faster search\n\n## Goal\n\nFast.\n\n## Done when\n\n- fast\n\n"
        f"## Non-goals\n\n- caching\n\n## Roadmap\n\n{roadmap}"
    )
    return text.replace("\n", newline)


def test_scenario_planned_roadmap_line(project: Workspace) -> None:
    """Requirement "New change in a milestone": a planned line becomes a link."""
    project.write(MILESTONE_FILE, faster_search("- add-limit: cap the results\n- add-cache\n"))
    done = setup.create_change(
        project.root, "add-limit", milestone="faster-search", today=datetime.date(2026, 11, 20)
    )
    assert 'linked from the roadmap of "faster-search"' in done.message
    proposal_text = project.read("changes/add-limit/proposal.md")
    assert "- Owner: Sam Doe\n- Milestone: faster-search\n\n" in proposal_text
    assert project.read(MILESTONE_FILE).endswith(
        "## Roadmap\n\n- [add-limit](../../changes/add-limit/proposal.md): cap the results\n"
        "- add-cache\n\n## Log\n\n- (proposed) 2026-11-20 add-limit by Sam Doe\n"
    )
    found = check.check(project.root, datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC))
    assert [f.code for f in found if "milestone" in f.code] == []


def test_a_planned_line_with_only_the_name_becomes_a_link(project: Workspace) -> None:
    project.write(MILESTONE_FILE, faster_search("- [ ] add-limit\n"))
    setup.create_change(project.root, "add-limit", milestone="faster-search")
    assert "- [ ] [add-limit](../../changes/add-limit/proposal.md)\n\n## Log\n" in project.read(
        MILESTONE_FILE
    )


def test_scenario_change_not_on_the_roadmap(project: Workspace) -> None:
    project.write(MILESTONE_FILE, faster_search("- add-limits-v2: not this one\n\n"))
    setup.create_change(project.root, "add-limit", milestone="faster-search")
    assert (
        "- add-limits-v2: not this one\n- [add-limit](../../changes/add-limit/proposal.md)\n\n"
        "## Log\n"
    ) in project.read(MILESTONE_FILE)


def test_a_change_joins_an_empty_roadmap(project: Workspace) -> None:
    project.write(MILESTONE_FILE, faster_search(""))
    setup.create_change(project.root, "add-limit", milestone="faster-search")
    assert (
        "## Roadmap\n\n- [add-limit](../../changes/add-limit/proposal.md)\n\n## Log\n"
    ) in project.read(MILESTONE_FILE)


def test_the_milestone_keeps_its_line_endings(project: Workspace) -> None:
    project.write(MILESTONE_FILE, faster_search("- add-limit: cap\n", newline="\r\n"))
    setup.create_change(project.root, "add-limit", milestone="faster-search", short=True)
    text = project.read(MILESTONE_FILE)
    assert "\n" not in text.replace("\r\n", "")
    assert "- [add-limit](../../changes/add-limit/proposal.md): cap\r\n\r\n## Log\r\n" in text
    proposal_text = project.read("changes/add-limit/proposal.md")
    assert "- Milestone: faster-search\n- Path: short\n" in proposal_text


def test_scenario_unknown_milestone_refused(project: Workspace) -> None:
    project.write(MILESTONE_FILE, faster_search(""))
    before = project.read(MILESTONE_FILE)
    with pytest.raises(Refusal) as refusal:
        setup.create_change(project.root, "add-limit", milestone="no-such-milestone")
    assert '"no-such-milestone"' in str(refusal.value)
    assert "faster-search" in str(refusal.value)
    assert not project.path("changes/add-limit").exists()
    assert project.read(MILESTONE_FILE) == before


def test_a_change_joins_a_new_milestone_from_the_template(project: Workspace) -> None:
    setup.create_milestone(project.root, "faster-search")
    setup.create_change(project.root, "add-limit", milestone="faster-search")
    record = load_record(find_project(project.root))
    roadmap = record.milestones["faster-search"].roadmap
    assert roadmap is not None
    assert [entry.target for entry in roadmap.entries] == ["../../changes/add-limit/proposal.md"]
    problems = record.milestones["faster-search"].problems
    assert {problem.code for problem in problems} <= {"empty-section"}
    found = check.check(project.root, datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC))
    assert [f.code for f in found if "milestone" in f.code] == []


def test_scenario_change_written_after_another(project: Workspace) -> None:
    """Requirement "Change comes after another": wm new change --after writes the line."""
    setup.create_change(project.root, "add-limit")
    project.write(MILESTONE_FILE, faster_search(""))
    setup.create_change(project.root, "add-paging", milestone="faster-search", after="add-limit")
    assert "- Owner: Sam Doe\n- Milestone: faster-search\n- After: add-limit\n\n" in project.read(
        "changes/add-paging/proposal.md"
    )
    with pytest.raises(Refusal, match="not a valid change name"):
        setup.create_change(project.root, "add-sort", after="Add_Limit")
    assert not project.path("changes/add-sort").exists()


def test_scenario_new_resource(project: Workspace) -> None:
    """Requirement "Resource commands": wm new resource writes a valid file from the template."""
    done = setup.create_resource(project.root, "stripe", "service", datetime.date(2026, 11, 17))
    assert done.message == 'Created the resource "stripe".'
    assert done.paths == ("resources/stripe.md",)
    text = project.read("resources/stripe.md")
    for line in (
        "- Kind: service\n",
        "- Serves: none\n",
        "- Status: active\n",
        "- Verified: 2026-11-17\n",
    ):
        assert line in text
    for section in ("What it is", "Access", "Interface", "Data", "Configuration", "Verification"):
        assert f"## {section}\n" in text
    assert "Never store a secret" in text
    assert "Good: " in text
    assert "Bad: " in text
    assert [p for p in project.record().problems if p.path == "resources/stripe.md"] == []


def test_scenario_name_taken(project: Workspace) -> None:
    setup.create_resource(project.root, "stripe", "service")
    before = project.read("resources/stripe.md")
    with pytest.raises(Refusal, match='already is a resource named "stripe"'):
        setup.create_resource(project.root, "stripe", "platform")
    assert project.read("resources/stripe.md") == before


def test_scenario_unknown_kind_given(project: Workspace) -> None:
    kinds = "service, platform, account, database, dataset, document"
    with pytest.raises(Refusal) as refusal:
        setup.create_resource(project.root, "stripe", "repository")
    assert kinds in str(refusal.value)
    with pytest.raises(Refusal) as missing:
        setup.create_resource(project.root, "stripe", None)
    assert kinds in str(missing.value)
    assert not project.path("resources/stripe.md").exists()


def test_claude_code_is_detected_by_its_folder_or_its_memory_file(tmp_path: Path) -> None:
    """Item: a detection hook per adapter."""
    claude = adapters.get("claude-code")
    assert not claude.detect(tmp_path)
    (tmp_path / ".claude").mkdir()
    assert claude.detect(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "CLAUDE.md").write_text("# Notes\n", encoding="utf-8")
    assert claude.detect(other)
    (other / ".claude").write_text("not a folder", encoding="utf-8")
    assert claude.detect(other)


def test_an_adapter_detects_nothing_by_default(tmp_path: Path) -> None:
    class Bare(adapters.Adapter):
        name = "bare"
        title = "Bare"
        capabilities = adapters.Capabilities(skills=False, subagents=False, hooks=False)

        def files(self, existing: Mapping[str, str | None]) -> dict[str, str]:
            return {}

    (tmp_path / ".claude").mkdir()
    assert not Bare().detect(tmp_path)


def test_init_with_ci_writes_the_workflow_in_the_same_transaction(tmp_path: Path) -> None:
    git_init(tmp_path)
    done = setup.init_project(tmp_path, ci=True)
    workflow = tmp_path / ".github" / "workflows" / "waymark.yml"
    assert workflow.is_file()
    assert ".github/workflows/waymark.yml" in done.paths
    assert "Added .github/workflows/waymark.yml" in done.message
    assert 'run "wm ci"' not in done.message


def test_init_without_ci_writes_what_it_wrote_before(tmp_path: Path) -> None:
    git_init(tmp_path)
    plain = setup.init_project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    git_init(other)
    explicit = setup.init_project(other, ci=False)
    assert not (tmp_path / ".github").exists()
    assert sorted(plain.paths) == sorted(explicit.paths)
    assert 'run "wm ci"' in plain.message

"""Hard constraints on the package, checked against the source tree itself.

These hold from the first commit: Python 3.11 or newer, standard library only
at runtime, no network access, and nothing that depends on symlinks.
"""

import ast
import os
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "src" / "waymark"

NETWORK_MODULES = frozenset(
    {
        "ftplib",
        "http",
        "imaplib",
        "poplib",
        "smtplib",
        "socket",
        "socketserver",
        "ssl",
        "urllib.request",
        "webbrowser",
        "xmlrpc",
    }
)

SYMLINK_CALLS = frozenset({"symlink", "symlink_to"})

SKIPPED_DIRECTORIES = frozenset(
    {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", "dist"}
)


def load_pyproject() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def source_trees() -> Iterator[tuple[Path, ast.Module]]:
    files = sorted(SOURCE_ROOT.rglob("*.py"))
    assert files, f"no source files under {SOURCE_ROOT}"
    for path in files:
        yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(tree: ast.Module) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative imports are not used"
            assert node.module is not None
            yield node.module
            for alias in node.names:
                yield f"{node.module}.{alias.name}"


def is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def test_requires_python_3_11_or_newer() -> None:
    assert load_pyproject()["project"]["requires-python"] == ">=3.11"


def test_runtime_has_no_dependencies_beyond_the_standard_library() -> None:
    project = load_pyproject()["project"]
    assert project["dependencies"] == []
    assert "optional-dependencies" not in project


def test_source_imports_only_the_standard_library() -> None:
    allowed = sys.stdlib_module_names | {"waymark"}
    for path, tree in source_trees():
        for module in imported_modules(tree):
            top_level = module.split(".")[0]
            assert top_level in allowed, f"{path} imports {module}"


def test_source_imports_no_network_modules() -> None:
    for path, tree in source_trees():
        for module in imported_modules(tree):
            for banned in NETWORK_MODULES:
                assert not is_within(module, banned), f"{path} imports {module}"


def test_source_never_creates_symlinks() -> None:
    for path, tree in source_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in SYMLINK_CALLS, f"{path}:{node.lineno} uses {node.attr}"


def test_repository_contains_no_symlinks() -> None:
    for directory, subdirectories, files in os.walk(REPO_ROOT):
        subdirectories[:] = [name for name in subdirectories if name not in SKIPPED_DIRECTORIES]
        for name in [*subdirectories, *files]:
            path = Path(directory) / name
            assert not path.is_symlink(), f"{path} is a symlink"


def test_core_knows_no_agent_tool() -> None:
    """Only adapters may name an agent tool, its file paths or its events."""
    adapters = SOURCE_ROOT / "adapters"
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if adapters in path.parents:
            continue
        text = path.read_text(encoding="utf-8").casefold()
        assert "claude" not in text, f"{path} names an agent tool"


def test_only_the_record_model_touches_the_file_system() -> None:
    """Code outside the record model reads and writes the record through it."""
    record = SOURCE_ROOT / "record"
    file_calls = {
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
        "open",
        "unlink",
        "rename",
    }
    package_data = SOURCE_ROOT / "assets"
    for path, tree in source_trees():
        if record in path.parents or package_data in path.parents:
            continue
        for node in ast.walk(tree):
            name = node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)
            assert name not in file_calls, f"{path}:{getattr(node, 'lineno', 0)} uses {name}"

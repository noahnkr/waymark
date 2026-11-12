"""Shared fixtures."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.support import ATLAS_CONFIG, Workspace


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the machine's own git settings out of every test."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git_init(root: Path, name: str | None = "Sam Doe") -> None:
    """Make a folder a git repository, with a name to sign with unless told otherwise."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    if name is not None:
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", name], check=True, capture_output=True
        )


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    """A temporary project with the record in the repository."""
    return Workspace(tmp_path / "project")


@pytest.fixture
def atlas(tmp_path: Path) -> Workspace:
    """A temporary atlas that names two code repos."""
    return Workspace(tmp_path / "atlas", ATLAS_CONFIG)


@pytest.fixture
def project(workspace: Workspace) -> Workspace:
    """A temporary project inside a git repository, as the commands need it."""
    git_init(workspace.root)
    return workspace

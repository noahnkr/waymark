"""Shared fixtures."""

from pathlib import Path

import pytest

from tests.support import ATLAS_CONFIG, Workspace


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    """A temporary project with the record in the repository."""
    return Workspace(tmp_path / "project")


@pytest.fixture
def atlas(tmp_path: Path) -> Workspace:
    """A temporary atlas that names two code repos."""
    return Workspace(tmp_path / "atlas", ATLAS_CONFIG)

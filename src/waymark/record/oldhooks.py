"""The git hooks wm 0.1.1 installed, and removing them from a clone.

wm no longer installs git hooks. A clone set up by 0.1.1 has them in
``.waymark/hooks/``, with ``core.hooksPath`` pointing there; both are this
clone's own, so each clone removes its own. Any other hook setup is left alone.
"""

import shutil
from pathlib import Path

from waymark.record import git

HOOKS_DIR = ".waymark/hooks"
"""Where wm 0.1.0 and 0.1.1 kept the git hooks, relative to the repository's top."""


def _is_old_hooks_path(value: str | None) -> bool:
    return value is not None and Path(value).as_posix().rstrip("/") == HOOKS_DIR


def remove_old_hooks(root: Path) -> bool:
    """Remove the git hooks wm 0.1.1 installed in this clone; True when there were some.

    Only when ``core.hooksPath`` is ``.waymark/hooks``: the setting is unset,
    the folder deleted, and ``.waymark/`` too when nothing else is in it.
    """
    if not _is_old_hooks_path(git.config_value(root, "core.hooksPath")):
        return False
    git.unset_config(root, "core.hooksPath")
    folder = root / HOOKS_DIR
    if folder.is_dir():
        shutil.rmtree(folder)
    parent = folder.parent
    if parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
    return True

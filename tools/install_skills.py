"""Installs the maintainer skills into this machine's agent tool folders.

    python -m tools.install_skills

The maintainer skills, for working on Waymark itself (docs, releases), are kept
in ``tools/skills/`` and committed. An agent tool reads skills from its own
folder, which is per machine and never committed, so each contributor installs
them after ``wm init``, and again whenever ``tools/skills/`` changes. Only the
maintainer skills' own folders are written; nothing else in the tool folder is
touched, and the skills ``wm`` installs are left to ``wm init``.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "skills"
TARGETS = (".claude/skills",)
"""Where each agent tool reads skills from, relative to the repository."""


def maintainer_skills(source: Path = SOURCE) -> list[Path]:
    """The skill folders under the source, each holding a SKILL.md."""
    return sorted(path for path in source.iterdir() if (path / "SKILL.md").is_file())


def install(root: Path = ROOT, source: Path = SOURCE) -> list[str]:
    """Copy every maintainer skill into each target folder; one line per skill and target."""
    report = []
    for target in TARGETS:
        for skill in maintainer_skills(source):
            destination = root / target / skill.name
            existed = destination.exists()
            if existed:
                shutil.rmtree(destination)
            shutil.copytree(skill, destination)
            state = "updated" if existed else "created"
            report.append(f"{state}: {target}/{skill.name}")
    return report


def main() -> int:
    for line in install():
        print(line)
    print("Maintainer skills installed. Restart your agent session to pick them up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

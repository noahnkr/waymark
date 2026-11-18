"""Reading another atlas's specs, read only, where the atlas sits on this machine."""

from waymark.record.artifacts.config import CONFIG_FILE, RECORD_DIR
from waymark.record.machine.atlas import Found, locate_atlas
from waymark.record.machine.project import Project
from waymark.record.machine.registry import load_registry
from waymark.record.record import Record, load_record
from waymark.services.common import Refusal, notice


def reference_record(record: Record, atlas: str) -> Record:
    """Another atlas's record, read where it sits on this machine. It is only read."""
    references = {ref.atlas: ref for ref in record.config.references} if record.config else {}
    if atlas not in references:
        listed = ", ".join(sorted(references)) or "none"
        raise Refusal(
            f'This project references no atlas "{atlas}" (references: {listed}). Add a '
            f'"[references.{atlas}]" table to {RECORD_DIR}/{CONFIG_FILE} to read its specs.'
        )
    location = locate_atlas(
        atlas, load_registry(), record.project.root, references[atlas].path_hint
    )
    if location.folder is None:
        raise Refusal(location.detail)
    if location.found is Found.HINT:
        notice(f"{location.detail} ({location.folder})")
    return load_record(Project(location.folder))

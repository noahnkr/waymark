# Add spec background: design

## Context

`record/specs.py` reads a spec's sections strictly: Purpose and Requirements, and any other `##` heading is a problem. `record/deltas.py` reads a delta's optional sections (Purpose, ADDED, MODIFIED, REMOVED, RENAMED), reports an empty Purpose, and at archive or sync writes the delta into the spec: `_set_purpose` replaces the Purpose's body, `_new_spec_text` writes a new spec, and the already-applied check compares each part with the spec. `services/context.py` gives the implement and review packs the deltas and the living requirements they touch; `views/render.py` renders the packs' text; the specs step's guidance is a list in `services/instructions.py`.

## Approach

1. **Reading.** `Spec` and `Delta` each gain `background: str | None`, read from an optional `## Background` section; an empty one is an error that says so, as for Purpose.
2. **Writing.** At archive or sync, a delta with a Background sets the spec's: the section's body is replaced like the Purpose's, or, when the spec has none, a `## Background` section is inserted right before `## Requirements`. `_new_spec_text` writes the Background after the Purpose for a new spec. The already-applied check compares the Background too, so a sync re-run doesn't write it twice.
3. **Packs.** The implement and review packs get `backgrounds`: one entry per spec the change has a delta for, `{"spec": <name>, "text": <text>}`, from the delta's Background or else the living spec's, leaving out specs with neither. A field added, so the schema versions stay. The text output renders each under the spec's name, after the requirements.
4. **Guidance.** The delta template gets a `## Background` section with a comment: facts about the area that aren't requirements, a good and a bad example, and "remove this section unless the change sets the Background". The specs step's guidance gets one rule: what the system does is a requirement, a fact about the area its Background, a fact about an outside system a resource, and a fact for the whole project the charter's Context. `wm-propose` says the same where it drafts the deltas.
5. **Docs.** `record.md` adds Background to the spec's sections and the delta's; `concepts.md` gives the four places a fact goes; `json.md` is regenerated; the CHANGELOG notes it.

## Decisions

### Decision: How a Background changes
- **Status:** decided
- **Decided by:** human
- **Options:** through a delta, replaced whole like the Purpose; edited by hand like a resource, with a hole in the spec guard
- **Choice:** through a delta
- **Why:** a Background changes rarely, and a spec stays whole behind one gate; the delta already carries the Purpose the same way

### Decision: Where a Background sits
- **Status:** decided
- **Decided by:** planner
- **Options:** after the Purpose, before the Requirements; at the end of the spec
- **Choice:** after the Purpose
- **Why:** it is read before the requirements it explains, and it keeps the requirements the last section, where added requirements are appended

### Decision: Which Background the packs carry
- **Status:** decided
- **Decided by:** planner
- **Options:** the delta's when it has one, otherwise the spec's; always the living spec's
- **Choice:** the delta's when it has one
- **Why:** the agents build toward the spec as it will read once the change is archived, as they do for modified requirements

## Open questions

None.

## Risks and trade-offs

- A requirement could be written as Background to dodge a scenario. The guidance draws the line, and the review reads the deltas.
- Two changes in flight that both set one spec's Background don't conflict; the one archived last wins, as for the Purpose.
- With add-resources in flight on its own branch, the packs gain two fields in two changes; whichever merges second rebases onto the first.

# Add spec background

- Owner: Noah Roberts
- Review: independent

## Why

Some facts matter to one area of a project and to no other, and can't be found in the code or in the requirements: that a business's leads come from A Place for Mom bears on the lead funnel, not on the applicant tracker. Today such a fact has two homes, both wrong. In the charter's Context it reaches every agent on every change, and the Context grows with every area. In a requirement it reads as something the system must do, when it is a fact the requirements rest on. In shs-nexus's earlier record these facts sat in the specs among the requirements, with nothing to tell them apart.

A spec already scopes its area: a change that touches the area has a delta for its spec, and its agents get that spec's requirements. A Background section in the spec gets a fact to exactly the agents working on that area.

## What changes

- A spec may have a `## Background` section, between Purpose and Requirements: the facts about its area that aren't requirements, aren't found in the code, and don't describe an outside system (those go in a resource).
- A delta may carry `## Background`; archiving or syncing the change sets the spec's Background to it, whole, as a delta's Purpose sets the spec's Purpose. `wm check` reports an empty Background section in a spec or a delta.
- The implement and review packs carry, for each spec the change has a delta for, its Background as it will read once the change is archived.
- The delta template and the `wm-propose` skill say what goes in a Background, and the specs-step guidance says where a fact goes: a requirement for what the system does, Background for a fact about the area, a resource for an outside system, the charter for the whole project.

## Non-goals

- No way to remove a spec's Background through a delta; a delta replaces it.
- No Background in the explore pack; it lists each spec's purpose and requirements, and `wm show` gives the rest.
- No scenarios or other structure inside a Background; it is prose and lists.
- No conflict check between two changes that both set a spec's Background; the one archived last wins, as for Purpose.

## Impact

- Specs: `authored-formats` (added), `agent-guidance` (added)
- User-visible:
  - specs and deltas may have a `## Background` section; `wm check` reports an empty one
  - archiving or syncing a delta with a Background sets the spec's Background
  - `wm context --for implement` and `--for review` carry the Background of each spec the change touches, in text and JSON
  - the delta template and the specs-step guidance describe the section
- Code: `record/specs.py`, `record/deltas.py`, `record/templates/delta.md`, `services/context.py`, `services/instructions.py`, `views/` (render, schemas), the `wm-propose` skill in `assets/`, the tests, and the docs (`record.md`, `concepts.md`, `json.md` generated, the CHANGELOG)

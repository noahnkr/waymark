# Add resources: design

## Context

Explorations are the closest kind of note today: written by hand outside any change, read by `record/explorations.py` with the outline helpers (`require_title`, `parse_facts`, `collect_sections`), loaded in `load_record` from a folder through `_load_markdown_folder`, and created by `setup.create_exploration` from a template. `wm new`, `wm ls` and `wm show` choose the kind of note from a fixed list in `cli.py` and `views/payloads.py`.

The edit guard (`hooks/decide.py`, `_edit`) refuses a planner's edit under `specs/`, every edit by a reviewer, and every edit by an implementer inside the record. The context packs are built in `services/context.py`: the explore pack lists specs, changes, milestones and explorations; the implement and review packs carry the charter's context, the deltas and the requirements they touch. Payload fields may be added without raising a schema's version (`docs/json.md`). The tasks step's sizing rules are a list in `services/instructions.py`. `RECORD_FOLDERS` in `record/record.py` names the folders that get a `.gitkeep`.

## Approach

1. **Reading resources.** A new `record/resources.py` parses a resource like an exploration: the title, the facts `Kind`, `Serves`, `Status` and `Verified` (each required), and the six required sections, reporting each missing one, an unknown kind (listing the six), a status other than `active` or `retired`, and a date not in `YYYY-MM-DD`. It keeps each section's text and the outline of every `##` and `###` heading. `Serves` is split with `split_names`; `none` means no specs. `load_record` loads `resources/` into `Record.resources` and adds the folder to `RECORD_FOLDERS`, so `wm init` and `wm update` write its `.gitkeep` with no other change to setup. `Record.documents()` yields resources, so links in them are checked like any other note's, and `wm check --fix` reaches them.
2. **Specs a resource serves.** Checked after loading, where the specs are known, like `_check_spec_repos`: a name in `Serves` that isn't a spec is an error on that line that lists the specs.
3. **Template and `wm new`.** `templates/resource.md` holds the title, the four lines with placeholders `wm` fills in (`{{kind}}`, `{{date}}`), a comment with the rule never to store secrets and a short good and bad example, and the six sections, each with a comment saying what goes there and to write `None.` when it doesn't apply, and that environments go in `###` subsections. `cli.py` adds `resource` to `wm new`'s kinds, with an optional third positional, the resource's kind, which `wm new resource` requires and the other kinds refuse. `setup.create_resource` checks the name and the kind, then writes the file in one transaction.
4. **`wm ls` and `wm show`.** `resources` joins `wm ls`'s choices and `resource` joins `wm show --kind`. The list shows name, kind, status and served specs; `show` prints the whole file, with its lines at the top as for an exploration. Both get JSON payloads (`wm.ls` rows, a new `wm.show.resource`), described in `views/schemas.py` and so in `docs/json.md`.
5. **Context packs.** The explore pack gets a `resources` list: name, title, kind, status and serves. The implement and review packs get a `resources` list: for each active resource whose `Serves` names a spec the change has a delta for, its name, kind, the text of What it is and Access, the outline of the other headings, and the command `wm show <name> --kind resource`. Text output renders the same lists. The fields are additions, so the schema versions stay.
6. **The edit guard.** In `_edit`, an edit under `resources/` by the planner or an implementer is allowed before the implementer refusal; a reviewer is still refused first. The records-only-by-wm check doesn't apply, since resources hold no records.
7. **Guidance and skills.** The tasks step's sizing rules get the resource rule. The `wm-propose` skill says a change that sets up or alters something outside the repo gets a resource item, and that a fact about an outside system belongs in a resource, not a spec. `wm-explore` reads resources from the index when the idea touches one. `wm-apply` says to update the resource and its `- Verified:` date when an item changes something outside the repo.
8. **Docs.** `record.md` gets a Resource section and the folder in its tree; `concepts.md` gets the term; `cli.md` and `json.md` are regenerated; the CHANGELOG gets an Unreleased entry.

## Decisions

### Decision: Where the kind comes from on `wm new`
- Status: decided
- Decided by: human
- Options: a required argument (`wm new resource stripe service`); a placeholder that fails `wm check` until filled; a default kind of `service`
- Choice: a required argument, with `- Serves: none`, `- Status: active` and `- Verified:` set to the day it runs
- Why: the new file is valid from the start without guessing its kind; the planner creates a resource from facts it has just looked at, so today is its verified date

### Decision: How resources are changed
- Status: decided
- Decided by: human
- Options: edited by hand like docs, inside or outside a change; changed only through a change, with resource deltas accepted and archived like spec deltas
- Choice: edited by hand, with an item in a change that alters something outside the repo
- Why: a resource records what the outside world is, not what is intended, so there is nothing to accept up front; drift outside any change is recorded at its own size, and a change's edits are seen in its review

### Decision: How environments are held
- Status: decided
- Decided by: human
- Options: one note per environment; one note per account or deployment, with environments as `###` subsections
- Choice: one note per account or deployment, environments as subsections; separate accounts and separate deployments get separate notes
- Why: dev and prod of one deployment share almost everything, and splitting them duplicates it; `wm` doesn't read the subsections, so they need no format

### Decision: Sections when they don't apply
- Status: decided
- Decided by: human
- Options: the six sections always present, `None.` when they don't apply; sections chosen per kind
- Choice: always present
- Why: one layout for every kind is easy to check and to search, and kinds differ only in which sections hold the most

### Decision: What the implement and review packs carry
- Status: decided
- Decided by: human
- Options: the full text of each serving resource; What it is, Access and the outline, the rest read on demand; an index only
- Choice: What it is, Access and the outline
- Why: the agent always knows what exists and how to reach it, without the bulk of tables it may not need; an index alone depends on the agent noticing

### Decision: How the edit guard admits implementers
- Status: decided
- Decided by: human
- Options: implementers may edit resources only; implementers may edit nothing in the record, and the planner builds every resource item
- Choice: resources only
- Why: a resource item can then be delegated like any other, while the rest of the record stays closed to implementers

### Decision: Where the resource rules live in the specs
- Status: decided
- Decided by: planner
- Options: a new `resources` spec; the layout in `authored-formats` and the behavior spread over `records`, `setup` and others
- Choice: a new `resources` spec, with only the edits other specs already own (the tiny path, implementer edits, folders, sizing rules) made in theirs
- Why: one place to read what a resource is; `authored-formats` stays about the notes written for a change

## Open questions

None.

## Risks and trade-offs

- Resources aren't gated by acceptance, so a resource and a spec can disagree. The guidance draws the line: a spec says what the system does, a resource what the outside world is.
- A resource can go stale without anyone noticing; the `- Verified:` date shows its age, and a staleness warning is left for later.
- Secrets could be written into a resource. Only the template and the docs warn against it.
- `wm new`'s optional third positional applies only to resources, which makes the command's help slightly less uniform.

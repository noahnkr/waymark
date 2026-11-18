# Add resources

- Owner: Noah Roberts
- Milestone: context-beyond-the-code
- Review: independent

## Why

Much of what an agent needs to build a project lives outside the repo, and can't be found from the code or the specs: the outside services the code talks to and how they behave (their limits, formats, ids and quirks), the platforms it is deployed on, the accounts it signs in with, the datasets it loads, and documents such as the copy a feature was built from. The record has no place for these facts. Charter goal 1 says a missing fact is written into the record, but a fact about an outside system has nowhere to be written, so it ends up in a spec, where it is mixed with what the system itself does and can change only through a change, or it stays in someone's head.

The shs-nexus project shows the size of the gap: a project built on WelcomeHome, WellSky, GoTo, Gmail, Supabase and Cloudflare, whose earlier record kept 13 notes on outside systems, and whose spec for the WelcomeHome connector is mostly a description of WelcomeHome. Waymark is to support projects like it, and resources are the clearest addition for that.

## What changes

- A new kind of note, a **resource**: `waymark/resources/<name>.md`, the as-built facts about one thing outside the repo. One note per account or separate deployment; environments of the same thing are subsections within one note.
- Every resource has the same layout: a title; the lines `- Kind:`, `- Serves:`, `- Status:` and `- Verified:`; and six sections, always present, written `None.` when they don't apply: What it is, Access, Interface, Data, Configuration and Verification.
- A resource's kind is one of `service`, `platform`, `account`, `database`, `dataset` or `document`. There is no repository kind: an atlas covers other repositories.
- `- Serves:` names the specs the resource serves, or `none`; `wm check` reports a name that isn't a spec.
- Resources are edited like docs, not specs: the planner edits them at any time, inside a change or outside one as tiny work, and an implementer may edit them, though nothing else in the record. A change that sets up or alters something outside the repo gets its own item to update the resource.
- `wm new resource <name>`, `wm ls resources` and `wm show <name> --kind resource` work as for the other notes.
- The explore pack gets an index of the resources. The implement and review packs get, for each active resource that serves a spec the change has a delta for, its What it is and Access sections and the outline of its headings; the agent reads the rest with `wm show`. Retired resources are left out of the packs.
- `wm init` and `wm update` keep `resources/` in git with a `.gitkeep`, like the other six folders. The record format stays 1.

## Non-goals

- No check for secrets. The rule never to store them is in the template and the docs; any scan would have to guess.
- No staleness warning from the `- Verified:` date.
- No reading another atlas's resources with `--from`.
- No Background section in specs, for facts outside the code that are neither requirements nor resources; that is a separate change.
- No conversion of shs-nexus's existing resource notes.

## Impact

- Specs: `resources` (new), `paths` (modified), `records` (modified), `setup` (modified), `step-guidance` (modified)
- User-visible:
  - a new folder, `waymark/resources/`, holding resources, with a `.gitkeep` written by `wm init` and `wm update`
  - `wm new resource`, `wm ls resources` and `wm show --kind resource`
  - `wm check` holds resources to their layout, kinds, status, date and the specs they serve
  - `wm context` packs carry an index of resources (explore) and the resources serving the change's specs (implement, review), in text and JSON
  - an implementer may edit resources; tiny work may edit resources
  - the tasks guidance asks for an item to update a resource when a change alters something outside the repo
- Code: `record/` (a new resources module, `record.py`, `templates.py`, a new `templates/resource.md`), `services/setup.py`, `services/context.py`, `services/instructions.py`, `views/` (payloads, schemas, render), `hooks/decide.py`, `cli.py`, the `wm-propose`, `wm-explore` and `wm-apply` skills in `assets/`, the tests, and the docs (`record.md`, `concepts.md`, `cli.md` and `json.md` generated, the CHANGELOG)

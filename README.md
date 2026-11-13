# Waymark

**Spec-driven development for developers who stay in charge of their project while
agents write the code.** Waymark keeps a written record of your project (living
specs, and the changes being made to them) in plain markdown in your repository.
A deterministic command, `wm`, reads that record and tells your coding agent what
to do next. The model of living specs plus change deltas comes from
[OpenSpec](https://github.com/Fission-AI/OpenSpec); Waymark adds firm points
during the build.

## What is different

- **Agents only know what is written down.** Each piece of code is built by a
  fresh agent that starts from the record and nothing else: no chat history, no
  hand-written briefing. When the record isn't enough, the agent reports a spec
  gap instead of guessing.
- **Review is recorded, and independent where it matters.** Every task item is
  checked at its review level (a self-check, an independent reviewer agent that
  never saw how it was built, or none for trivial work), and the check is written
  under the item. Archiving a change is refused while a review is missing.
- **Any session can pick up where the last one stopped.** There is no stored
  status. `wm` works out where things stand, and the next step, from the files
  and git alone, on any machine.
- **You decide; agents write.** Agents draft every proposal, spec delta, design
  and task list, and write the code. You approve a change before any code is
  written, and you approve it again when it is archived.

## What it looks like

<!-- generated: evidence -->

*Real output of this version of `wm`, from a small generic change made for this README by `tools/docs.py`. From 0.1.1 it comes from Waymark's own record.*

One change on the short path, accepted, with its first item built and self-reviewed:

```console
$ wm status
── Changes in flight ───────────────────────────────────────────────────
  add-result-limit         applying   █████░░░░░ 1/2    → apply 1.2

✓ Nothing needs you.
```

The change's folder:

```
waymark/changes/add-result-limit/proposal.md
waymark/changes/add-result-limit/specs/search.md
waymark/changes/add-result-limit/tasks.md
```

`wm accept` wrote this line into the proposal: `Accepted: 2026-01-15 by Alex Example (fingerprint: d042f9b4cd32eca7)`

And the task list, where wm wrote the tick and the self-review under item 1.1:

```markdown
# Tasks

## 1. Limit

- [x] 1.1 Cap the result count
  - Criteria: at most fifty results come back
  - Verify: a test searches an index with fifty-one matches
  - (self-review) 2026-01-15: the cap holds at fifty; the fifty-one-match test passes
- [ ] 1.2 Mention the limit in the help text   `review: none`
  - Criteria: the search help names the limit
```

<!-- end of generated evidence -->

## How a change goes

```
explore    optional: think an idea through; nothing is written unless you ask
propose    why, what, non-goals and impact
specs      deltas against the living specs
design     how, and the decisions taken (skipped on the short path)
tasks      one checklist; each item has criteria and a review level
accept     you approve the change; no code is written before this
apply      each item built by a fresh agent from the record alone
review     each item checked at its level, and the check written down
archive    you archive it; the deltas merge into the specs
```

Small work takes the **short path**: a proposal and a task list, no design, and
self-review or none. Bigger or riskier work gets a design and independent review.
The [concepts guide](docs/concepts.md) explains each step, file and rule.

## Who it is for

- **Solo developers** building real projects with coding agents, who want to own
  the design and delegate the typing.
- **Small teams** (roughly two to five people) sharing one record, each running
  their own changes on their own branches.
- **Projects that span several repositories**, such as a frontend and a backend,
  with one shared record in an *atlas* ([multi-repo guide](docs/multi-repo.md)).
- **New and existing codebases alike.** On an existing codebase, specs grow only
  where work happens; nothing is reverse-engineered up front.

It is **not** for handing over a goal and walking away, for throwaway prototypes
and one-off scripts, or for organizations that need access control, approval
chains or an issue-tracker integration.

## What it costs

- **Agents write** every artifact (proposals, deltas, designs, task lists) and
  all the code, using your own agent tool and plan. `wm` never calls a model.
- **You approve** each change twice: when you accept it, and when you archive
  it. In between, `wm inbox` lists the few things only you can settle: spec
  gaps, blocked items, and reviews that failed twice.
- **Time and tokens:** measured figures come from using Waymark on itself and
  arrive with version 0.1.1. None are claimed before they are measured.

## What is enforced, and where

| Enforced by | What | Holds in |
|---|---|---|
| `wm` itself, the git hooks and CI | Acceptance before any item is applied; archiving refused while a review, a tick or the acceptance is missing; conflicting changes detected; record health (`wm check`); commit-message format | Every agent tool, and outside any tool |
| Claude Code's hooks | Agents can't accept a change or override the archive gate; the implementer edits only code (in its item's repository) and its own notes; the reviewer edits nothing; delegated agents can't commit, push or run writing `wm` commands; agents must end with their result or verdict, which `wm` records | Claude Code only. In a tool without hooks the workflow runs on trust, and the core gates still hold. |

**These are guard rails, not security.** They stop mistakes, drift and shortcuts,
and `wm check` makes hand-made evidence visible. They don't stop someone, or an
agent with a shell, set on getting around them.

**Teams:** several people can each run changes at once. Each change has one
owner; changes merge through ordinary git branches; two changes that touch the
same requirement are reported by `wm check`, and the second to be archived must
be revised first. Conflicts are caught on the merged tree and at archive, not
before merge, and the independent reviewer is always an agent, not a person.

## Install

Waymark needs Python 3.11 or newer and has no dependencies beyond the standard
library. The package is **`waymark-cli`** (an unrelated project owns the name
`waymark` on PyPI); the command is `wm`:

```
pipx install waymark-cli
# or
uv tool install waymark-cli
```

Each project pins the exact `wm` version it uses; `wm` tells you the install
command when yours differs. Then follow [getting started](docs/getting-started.md).

## Agent tools

Version 0.1.0 works with **Claude Code**: `wm init` writes the skills, the two
agent definitions and the hooks into the project. The core is tool-neutral, and
other tools can be added as adapters.

Claude Code version last verified: **pending the 0.1.0 smoke test**.

## Documentation

- [Getting started](docs/getting-started.md): install, set up a project, run a first change
- [Concepts and glossary](docs/concepts.md): the workflow, the files, the roles and the rules
- [Multi-repo guide](docs/multi-repo.md): one record for a frontend and a backend
- [CLI reference](docs/cli.md) and [JSON schema reference](docs/json.md), generated from the code
- [Architecture notes](docs/architecture.md): for contributors, including how to add an adapter
- [Smoke-test checklist](docs/smoke-test.md): the live check run before each release
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE)

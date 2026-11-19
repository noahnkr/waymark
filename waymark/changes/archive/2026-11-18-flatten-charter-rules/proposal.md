# Flatten charter rules

- **Owner:** Noah Roberts
- **Milestone:** context-beyond-the-code
- **Review:** independent

## Why

The charter's Rules are split under a heading per workflow step, and each agent gets only its own step's rules. The split buys little and costs something. A project has few rules of its own (this one has eight, over five steps), so giving every agent all of them adds a few lines, while splitting them hides rules from the agents that need them: the reviewer gets only the `### Review` rules, empty here, so it never sees that the full checks must pass or that generated docs are never hand-edited, which is just what a review holds the build to. Writing a rule also means guessing which one step it belongs to, when most rules bear on several.

The context-beyond-the-code milestone gives each kind of fact one place: the charter for the whole project, a spec's Background for one area, resources for the world outside. Rules for the whole project belong in the charter as one list, like its goals and constraints.

## What changes

- The charter's `## Rules` is one numbered list, `1. <rule>`, like Goals and Constraints. `wm check` reports any other line in it, a step heading included, with the form expected.
- `wm instructions` gives the whole list at every step, and `wm context` gives it in every pack: explore, implement and review.
- The charter template writes `## Rules` with a comment and an example, and no step headings.
- This repository's charter is rewritten to the list. No migration: it is the only record there is.
- The `wm-kickoff` skill asks for the project's rules as one list, and the skills and docs no longer speak of a step's rules.

## Non-goals

- No tags or scoping on a rule. A rule that matters to one area of the project goes in that spec's Background, in add-spec-background.
- No migration of a charter with step headings, and no `wm check --fix` for one.
- No change to the shared rules, the severity rubric or the stopping rules that `wm` itself gives.
- The `rules` field in the JSON payloads keeps its name and type.

## Impact

- **Specs:** `authored-formats` (modified, renamed), `step-guidance` (added), `agent-guidance` (added)
- **User-visible:**
  - the charter's Rules are a numbered list; a step heading or bullet under Rules is a `wm check` error
  - `wm instructions` and every `wm context` pack give all the project's rules, not one step's
  - `wm init` writes the charter's Rules without step headings
- **Code:** `record/charter.py`, `record/templates/charter.md`, `services/instructions.py`, `services/context.py`, the `wm-kickoff`, `wm-explore` and `wm-apply` skills in `assets/`, this repository's `waymark/charter.md`, the tests, and the docs (`record.md`, `concepts.md`, the CHANGELOG)

## Outcome

- **Built:** The charter's Rules are one numbered list, checked like Goals and Constraints, and a step heading or bullet under them is reported. wm instructions and every context pack give the whole list under Project rules. The charter template, this repo's charter, the kickoff, explore and apply skills, the agent definitions, the docs and the CHANGELOG all describe one list for every agent.
- **Differs:** One suggestion from the independent review is left open: the module docstring in services/context.py still says the packs carry apply rules and review rules. The explore pack's text also shows the Rules once, under Project rules, rather than as a charter section as well.

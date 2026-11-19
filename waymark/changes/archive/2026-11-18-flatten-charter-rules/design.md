# Flatten charter rules: design

## Context

`record/charter.py` reads `## Rules` into `Charter.rules`, a map from each workflow step to the text under its `###` heading, and reports an unknown or repeated step heading. `services/instructions.py` gives a step's text as `rules` (for explore and for each change step), and `services/context.py` gives the explore, apply and review texts to the three packs. `views/render.py` titles them "Rules for this step" in the instructions text and "## Rules for this step" in the implement and review packs; the explore pack's text shows the charter's sections as they are. The numbered-list check for Goals and Constraints lives in the charter reader, and the charter template writes the eight step headings.

## Approach

1. **Reading.** `Charter.rules` becomes a string: the body of `## Rules`, checked by the same numbered-list check as Goals and Constraints, which reports any other line, a `###` heading included, with the form `1. <text>`. The step-heading parsing and its two problem codes, `unknown-step` and the repeated-step one, go.
2. **Giving.** `instructions.py` and `context.py` give `charter.rules` whole wherever they gave one step's text; the `rules` field keeps its name and type, so no schema version changes. `render.py` titles it "Project rules", and leaves it out when empty, as today.
3. **Template.** `templates/charter.md` writes `## Rules` with a comment saying they reach every agent at every step, and a good and a bad example, and no step headings.
4. **This repository's charter.** Rewritten in the same item as the reader, so the record stays healthy: the eight rules become one numbered list, in the order propose, specs, tasks, apply, archive.
5. **Skills and docs.** `wm-kickoff` asks for the rules as one list; `wm-explore` and `wm-apply` say "the project's rules" instead of "rules for this step"; `record.md` and `concepts.md` describe one list given to every agent; the CHANGELOG notes it.

## Decisions

### Decision: Rules as one list or scoped
- **Status:** decided
- **Decided by:** human
- **Options:** one list for every agent; step headings as today; tags on each rule naming the steps or areas it applies to
- **Choice:** one list for every agent
- **Why:** a project has few rules, so every agent can get all of them, and scoping hid rules from the agents that needed them; a fact for one area goes in its spec's Background instead

### Decision: Numbered or bulleted
- **Status:** decided
- **Decided by:** human
- **Options:** a numbered list like Goals and Constraints; a bullet list
- **Choice:** numbered
- **Why:** the charter's lists read alike, the existing check covers it, and a review can cite a rule by number

### Decision: Charters with step headings
- **Status:** decided
- **Decided by:** human
- **Options:** report them as errors with no migration; flatten them in `wm check --fix` or `wm update`
- **Choice:** report them as errors, with no migration
- **Why:** this repository's record is the only one, and it is rewritten in this change

### Decision: The `rules` field
- **Status:** decided
- **Decided by:** planner
- **Options:** keep `rules` as a string holding the whole list; make it a list of strings, one per rule
- **Choice:** keep it a string
- **Why:** no payload changes shape, so no schema version is raised; agents read the list as written

## Open questions

None.

## Risks and trade-offs

- Every agent reads every rule, so a rule written for one step may be read at another; with a handful of rules, the cost is a few lines.
- A project with many rules would bloat every pack. The guidance points rules for one area to that spec's Background.

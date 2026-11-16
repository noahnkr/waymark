# Lighter workflow

## Goal

Make Waymark's own workflow cost about what the change is worth. The planner builds items in the session, and each change gets one review, one full test run and one pull request. The work scales with the size of the change: tiny, short or full. The human's approval at accept and evidence written only by `wm` stay as they are.

## Done when

- By default the planner builds items itself. A fresh implementer runs only for items tagged for delegation.
- Review happens once per change, against the deltas' scenarios. The reviewer agent runs only for risky changes: ones that modify or remove a requirement, or touch data integrity.
- Each item runs only the tests it touches, and the full checks run once before the pull request.
- A change is archived on its own branch, so it takes one pull request.
- A tiny change is just a conventional commit with no change folder. The proposal names its path, and `wm check` holds each path to its rules.
- Acceptance is withdrawn only when something already accepted changes, not when an item is added.
- A short change measured on Waymark itself, from proposal to merge, takes 15 minutes or less and 150k tokens or less. The README's "What it costs" shows the figures.

## Non-goals

- Dropping `wm accept`, or letting agents write evidence.
- Regenerating code from specs.
- Calling a model from `wm`, or any other relaxation of the charter's constraints.

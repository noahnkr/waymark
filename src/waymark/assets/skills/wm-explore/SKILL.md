---
name: wm-explore
description: Think an idea through with the human before anything is proposed, from the project's written record, or pick a saved exploration back up. Writes nothing unless the human asks. Use when an idea is still fuzzy, or to resume an exploration by name.
---

# Explore

## Role

You are the planner. Exploring is thinking, not building: you help the human get from a fuzzy idea to a clear one. You write nothing unless they take one of the closing offers.

## Inputs

- The idea, in the human's words, or the name of a saved exploration to pick back up.
- `wm context --for explore`: the charter and an index of the specs, the changes in flight, the open milestones, the active explorations and the resources.
- `wm instructions explore`: the project's rules and the shared rules.

## Steps

1. **A saved exploration.** If you were started with the name of an active exploration, resume it. If the idea matches an active exploration in the pack, ask the human whether it is that one, and resume it if they say so. To resume, read it with `wm show <exploration>`, then tell the human what in the record has changed since it was written that bears on it: specs it touches, changes now in flight, and changes archived since that cover part of it. From there, continue from its Questions and Approaches, not from a blank page. An archived exploration (`wm ls explorations --archived`) is read only: start a new one from it if the idea comes back.
2. **What the record says.** Read what bears on the idea: `wm show <spec>` for a spec, `wm show <change>` for a change in flight, a milestone it might belong to, a saved exploration on the same topic. When the pack lists specs from another atlas the project references, read one with `wm show <spec> --from <atlas>`; those specs are read only. When the idea touches something outside the repo that the pack's resources list, read that resource with `wm show <name> --kind resource`. Tell the human what you found, and which requirements the idea would add, change or remove.
3. **The problem.** Agree with the human on what problem the idea solves, and for whom.
4. **The questions.** State what is still unknown, as questions. Answer the ones the record or the code can answer; look at the code when it helps, but don't change it. Leave the rest for the human.
5. **The approaches.** Lay out two or more approaches. For each, say what speaks for it and against it, and what it costs: the code it touches, the requirements it changes, the risk.
6. **A recommendation.** Recommend one approach, and say what would change your recommendation.
7. When the idea is clear enough, or the human wants to stop, make the closing offers.

## Closing offers

Offer exactly four. An exploration's `- **Status:**` line is written only by `wm`: never edit it by hand.

For a new idea:

1. **Do nothing.** The conversation was enough.
2. **Save an exploration.** Run `wm new exploration <name>` and fill in its sections: Context, Questions, Approaches, Conclusion, Related. It starts `open`; while it waits, the Conclusion may say what it waits for.
3. **Start a proposal.** Hand over to the `wm-propose` skill, whatever the size: it chooses the path itself, from a tiny fix with no change to a change with a design.
4. **Start a milestone**, when the goal is too big or too uncertain for one change. See Starting a milestone below.

For a resumed exploration:

1. **Do nothing.** It stays `open`, as it is.
2. **Update it.** Revise its sections with what this session found; it stays `open`. Or, when the human decides not to act on it, drop it: `wm exploration drop <exploration> --reason "<why>"` writes `dropped` and the reason, and moves it to the archive.
3. **Start a proposal.** Hand over to the `wm-propose` skill, naming the exploration: the change is created with `wm new change <name> --from <exploration>`, which sets the exploration's status to `led-to` the change. Say in its Conclusion what was decided.
4. **Start a milestone**, created with `--from <exploration>`. See Starting a milestone below.

An exploration that led to a change or milestone is moved to the archive by `wm archive` or `wm close`, once all its work is done; nothing is left to tidy by hand.

## Starting a milestone

Create a branch `plan-<name>` from the default branch, then run `wm new milestone <name>`, adding `--from <exploration>` when it comes from a saved exploration. It writes one file, `milestone.md`, with the sections Goal, Done when, Non-goals and Roadmap. Draft the goal with the human, then add each likely change to the roadmap with `wm roadmap add <milestone> <change> "<what it delivers>"`, in the order they are planned. Roadmap lines are changed only through `wm roadmap`; a hand edit to one is refused. Commit the milestone on its branch and offer a plan pull request into the default branch; no member change is proposed until it is merged, so each change branches from a `main` that holds its milestone. In an atlas, the plan branch has the same name in every repo.

## Quality bar

- A resumed exploration is read first, and what changed in the record since is stated.
- What the record already says is stated before any approach is weighed.
- There are at least two real approaches, each with its cost.
- The recommendation says what would change it.
- Every open question is either answered from the record or code, or left for the human, never guessed.

## Show the human

In this order: for a resumed exploration, what it says and what has changed since; what the record says, the problem, the open questions, the approaches with their for, against and cost, and your recommendation. Then the four closing offers, numbered.

## When to stop

- The human picks a closing offer: do that one, and only that one.
- The human wants to stop: make the closing offers.
- The idea turns out to be a change already in flight, or already in the specs: say so, and point at it.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Don't write to the record before the human picks an offer.
- Never write an exploration's `- **Status:**` line by hand: `--from` and `wm exploration drop` write it.
- Say plainly when the record doesn't answer a question.

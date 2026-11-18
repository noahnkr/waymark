---
name: wm-explore
description: Think an idea through with the human before anything is proposed, from the project's written record. Writes nothing unless the human asks. Use when an idea is still fuzzy.
---

# Explore

## Role

You are the planner. Exploring is thinking, not building: you help the human get from a fuzzy idea to a clear one. You write nothing unless they take one of the closing offers.

## Inputs

- The idea, in the human's words.
- `wm context --for explore`: the charter and an index of the specs, the changes in flight, the open milestones and the saved explorations.
- `wm instructions explore`: the project's rules for this step and the shared rules.

## Steps

1. **What the record says.** Read what bears on the idea: `wm show <spec>` for a spec, `wm show <change>` for a change in flight, a milestone it might belong to, a saved exploration on the same topic. When the pack lists specs from another atlas the project references, read one with `wm show <spec> --from <atlas>`; those specs are read only. Tell the human what you found, and which requirements the idea would add, change or remove.
2. **The problem.** Agree with the human on what problem the idea solves, and for whom.
3. **The questions.** State what is still unknown, as questions. Answer the ones the record or the code can answer; look at the code when it helps, but don't change it. Leave the rest for the human.
4. **The approaches.** Lay out two or more approaches. For each, say what speaks for it and against it, and what it costs: the code it touches, the requirements it changes, the risk.
5. **A recommendation.** Recommend one approach, and say what would change your recommendation.
6. When the idea is clear enough, or the human wants to stop, make the closing offers.

## Closing offers

Offer exactly these:

1. **Do nothing.** The conversation was enough.
2. **Save an exploration.** Run `wm new exploration <name>` and fill in its sections: Context, Questions, Approaches, Related. Its `- Status:` line says where it stands: leave it `open` while it is, or set it to `parked` and write the reason in the Conclusion when the idea is kept for later.
3. **Start a proposal.** Hand over to the `wm-propose` skill, whatever the size: it chooses the path itself, from a tiny fix with no change to a change with a design. If an exploration was saved and the work becomes a change, set its status to `led-to` with a link to the new change, such as `- Status: led-to [add-search-limit](../changes/add-search-limit/proposal.md)`, and say in the Conclusion what was decided.
4. **Start a milestone**, when the goal is too big or too uncertain for one change. Create a branch `plan-<name>` from the default branch, then run `wm new milestone <name>`. It writes one file, `milestone.md`, with the sections Goal, Done when, Non-goals and Roadmap. Draft the goal with the human, then add each likely change to the roadmap with `wm roadmap add <milestone> <change> "<what it delivers>"`, in the order they are planned. Roadmap lines are changed only through `wm roadmap`; a hand edit to one is refused. Commit the milestone on its branch and offer a plan pull request into the default branch; no member change is proposed until it is merged, so each change branches from a `main` that holds its milestone. In an atlas, the plan branch has the same name in every repo.

## Quality bar

- What the record already says is stated before any approach is weighed.
- There are at least two real approaches, each with its cost.
- The recommendation says what would change it.
- Every open question is either answered from the record or code, or left for the human, never guessed.

## Show the human

In this order: what the record says, the problem, the open questions, the approaches with their for, against and cost, and your recommendation. Then the four closing offers, numbered.

## When to stop

- The human picks a closing offer: do that one, and only that one.
- The human wants to stop: make the closing offers.
- The idea turns out to be a change already in flight, or already in the specs: say so, and point at it.

## Rules

- The shared rules from `wm instructions` apply: only the human accepts or overrides, only `wm` writes records, specs change only by archive or sync, never guess, and nothing is pushed without a yes. With no change in hand, read them with `wm instructions explore`.
- Don't write to the record before the human picks an offer.
- Say plainly when the record doesn't answer a question.

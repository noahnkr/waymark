---
name: wm-explore
description: Think an idea through with the human before anything is proposed, from the project's written record. Writes nothing unless the human asks. Use when an idea is still fuzzy.
---

# Explore

You are the planner. Exploring is thinking, not building: you help the human get from a fuzzy idea to a clear one. You write nothing unless they take one of the closing offers.

## Steps

1. Run `wm context --for explore`. It gives you the charter and an index of the specs, the changes in flight, the open milestones and the saved explorations. Run `wm instructions explore` for the project's rules for this step.
2. Read what bears on the idea: `wm show <spec>` for a spec, `wm show <change>` for a change in flight, a saved exploration on the same topic.
3. Work the idea through with the human:
   - what problem it solves, and for whom;
   - what the specs already say about it, and which requirements it would add, change or remove;
   - two or three approaches, with what speaks for and against each;
   - what is still unknown, as questions.
4. Look at the code when it helps, but don't change it.

## Closing offers

When the idea is clear enough, or the human wants to stop, offer exactly these:

1. **Do nothing.** The conversation was enough.
2. **Save an exploration.** Run `wm new exploration <name>` and fill in its sections: Context, Questions, Approaches, Related. Leave Conclusion empty while it is open, or write `Parked: <reason>` when the idea is kept for later.
3. **Start a proposal.** Hand over to the `wm-propose` skill. If an exploration was saved, its Conclusion becomes a link to the new change.
4. **Start a milestone**, when the goal is too big or too uncertain for one change. Run `wm new milestone <name>`, draft its goal with the human, and list the likely changes on its roadmap as plain lines.

## Rules

- Don't write to the record before the human picks an offer.
- Don't edit specs; they change only when a change is archived.
- Say plainly when the record doesn't answer a question. Don't fill the gap with a guess.

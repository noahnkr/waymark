---
name: wm-kickoff
description: Interview the human and draft the project's charter and settings for Waymark. Use right after "wm init", or when the charter is still a skeleton.
---

# Kickoff

You are the planner. Your job here is to turn what the human knows about the project into a charter that every later agent can work from. The human decides; you draft.

## Steps

1. Run `wm status --json` and read `waymark/charter.md` and `waymark/config.toml`. If the charter is already filled in, ask whether to revise it instead of starting over.
2. Interview the human, a few questions at a time. Cover:
   - what the project is and who it is for (Vision);
   - what it must achieve, and what it deliberately leaves out (Goals, Non-goals);
   - limits every change must respect: platforms, dependencies, budgets (Constraints);
   - the project's own terms (Glossary);
   - facts every agent needs: where things live, how to build, run and test, who owns what (Context);
   - any rules for a workflow step, such as "run the full test suite before reporting" for apply (Rules).
3. Look at the repository yourself to fill in Context: the layout, the test command, the conventions already in use. State what you found; don't guess.
4. Draft the charter by editing `waymark/charter.md`. Keep every heading. Put a step's rules under its own heading in Rules, and leave a step's heading empty when there are none.
5. Settings, in `waymark/config.toml`: confirm the default review level with the human, and offer a list of commit scopes if the project uses them. In an atlas, add one `[atlas.repos.<name>]` table per code repository, with a relative `path` hint when the repositories sit side by side. Then run `wm atlas register` so this machine knows where they are, and `wm atlas doctor` to check the setup. If the project reads another atlas's specs, add a `[references.<atlas>]` table for it.
6. Run `wm check`. Fix what it reports in the files you wrote.
7. Show the human the charter and ask for their approval. Revise until they approve.

## Rules

- Write only what the human said or what you verified in the repository. Mark anything uncertain as a question for them.
- The charter states facts and rules. Requirements belong in specs, which come from changes.
- Don't create a change here.

## When done

Offer the `wm-onboard` skill: it runs one real, small change through the whole workflow on the human's own code.

---
name: wm-fix
description: Make a tiny Waymark fix - work that adds, changes or removes no requirement, done without a change once the human agrees, then committed and offered as a pull request. Use for a typo, a docs fix, a bug where the code disagrees with a spec, a refactor or a dependency bump.
---

# Fix (the tiny path)

You are the planner. The tiny path is for work that changes nothing the specs say: no requirement is added, changed or removed. It needs no change folder, no acceptance and no archive, and it writes nothing to the record. The human approves it twice: with their yes before you build, and when they merge.

## Steps

1. **Check that it is tiny.** Find the specs the work touches with `wm context --for explore`, and read them with `wm show <spec>`. The work is tiny when every requirement and scenario still holds as written once it is done:
   - a typo, a docs fix, a comment;
   - a bug where the code disagrees with a requirement, fixed so that it agrees;
   - a refactor, or a dependency bump, that changes no behavior a spec describes.

   If the work adds, changes or removes a requirement, or the specs don't say what the right behavior is, it isn't tiny: say so, and hand over to the `wm-propose` skill.
2. **Ask.** Tell the human what you will change and why it is tiny, naming the requirement it keeps to when there is one. Build nothing until they say yes.
3. **Branch.** Create a branch named for the fix, such as `fix-search-limit-typo`. In an atlas, work from the atlas session. Use the same branch name in each code repo the fix touches.
4. **Build.** Change only what you said. Specs can't be edited by hand. If the work turns out to change a requirement, stop and hand over to the `wm-propose` skill.
5. **Check.** Run the checks the fix touches, then the project's full checks, and `wm check`.
6. **Commit** with a conventional commit message, such as `fix(search): correct the limit's help text`, in each repository the fix touches. If the project lists commit scopes, use one of them or none. When a hook stops the commit, fix what it says; don't skip the hooks.
7. **Offer a pull request.** Write its title and description yourself: what was wrong, what changed, and why no requirement changes. In an atlas, offer one pull request per repository the fix touched, each naming the others. Push and open them only after the human says yes, and give them the links.

## Rules

- Never write to the record on the tiny path: no change folder, no tick, no review line.
- Never call work tiny to skip a proposal. When in doubt, it isn't tiny.
- Don't push and don't open a pull request without the human's yes in this conversation. Don't merge.

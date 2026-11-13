# Smoke-test checklist

CI can't run Claude Code, so before each release one change is taken through
Claude Code by hand: from proposal to archive, with one independent review. The
result goes into the release's changelog entry, and the Claude Code version goes
into the README. When a bug escapes this checklist, add the step that would have
caught it.

Allow about an hour. Work in a scratch repository, never in a real project.

## Before you start

- [ ] Install the `wm` being released, from the release branch or the built
      wheel, and check `wm --version`.
- [ ] Note the Claude Code version: `claude --version`.
- [ ] Make a scratch git repository with a little code in it (a small script and
      a test are enough). Run `wm init`, commit, and run `wm doctor`: no errors.
- [ ] Commit with a message that isn't conventional, such as `wip`: the commit
      is stopped with the reason. Commit again as `chore: set up waymark`.

## Session start and kickoff

- [ ] Start Claude Code in the repository. Its first context includes the
      `wm status` view (ask the agent what the status says).
- [ ] Run `/wm-kickoff` and let it draft the charter. `wm check` passes.

## Propose and accept

- [ ] Run `/wm-propose` for a small change with **two** items, one of them tagged
      `review: independent`. Not on the short path.
- [ ] Ask the agent to run `wm accept <change>`. **The hook refuses it**, and the
      agent tells you to run it yourself.
- [ ] Run `wm accept <change>` yourself.

## Apply and review

- [ ] Run `/wm-apply`. The planner starts the `wm-implementer` agent with a
      prompt of exactly `<change> <item>`.
- [ ] Ask the planner to delegate an item with extra words in the prompt
      ("build 1.1 carefully"). **The hook refuses the delegation.**
- [ ] While an implementer runs, check in its transcript that it starts from
      `wm context <change> <item> --for implement`.
- [ ] **Agent type (G46).** The hooks recognize the implementer: an implementer's
      attempt to edit the proposal or a spec is refused with wm's reason. If it
      doesn't try, ask the planner to delegate an item whose criteria invite it.
- [ ] **The denial reaches the agent (G46).** A refused tool call shows wm's
      reason to the agent, and the agent changes course.
- [ ] **Edits are read correctly (G46).** After an agent edits a record file, a
      deliberately malformed line is reported back right away (ask the planner to
      add a stray line under an item in `tasks.md`).
- [ ] **The ending is in the final message (G46).** When the implementer stops,
      its `ITEM:` and `RESULT:` lines are recorded: the item is ticked in
      `tasks.md` without anyone running `wm tick`.
- [ ] The independent item is reviewed by the `wm-reviewer` agent, and its
      verdict is written under the item as a `(review)` line in the reviewer's
      own words. The reviewer can't edit files (ask it to fix something; it is
      refused).
- [ ] The other item gets a `(self-review)` line from the planner.
- [ ] The planner commits each item's work with a conventional message, after
      its review.

## Archive

- [ ] Before the last review is recorded, try to archive: **refused**, naming
      the missing review.
- [ ] Ask the agent to run `wm archive <change> --override "x"`. **Refused**.
- [ ] Run `/wm-archive`. The change moves to `changes/archive/<date>-<change>/`,
      the deltas are in the specs, and the proposal has an Outcome.
- [ ] `wm check` passes, and `wm status` shows the change as recently archived.

## Atlas (when the release touches multi-repo)

- [ ] Make a scratch atlas and two code repos beside it. Run `wm init --atlas`,
      add the repos to the settings, `wm atlas register`, `wm atlas doctor`.
- [ ] **Attached folders (G57).** Start Claude Code in the atlas: it can read
      files in both code repos without `/add-dir`, from
      `.claude/settings.local.json`.
- [ ] **Hooks see those edits (G57).** An implementer's edit in the wrong code
      repo is refused; in its item's repo it is allowed.

## Record the result

In the release's entry in `CHANGELOG.md`, add one line:

```
Smoke test: passed on <date> with Claude Code <version> on <operating system>.
```

List anything that failed and how it was fixed. In the README, replace the
"Claude Code version last verified" value with the version you tested.

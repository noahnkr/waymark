# Smoke-test checklist

CI can't run Claude Code, so before each release one change is taken through
Claude Code by hand: from proposal to archive, with one independent review of
the whole change. The
result goes into the release's changelog entry, and the Claude Code version goes
into the README. When a bug escapes this checklist, add the step that would have
caught it.

Allow about an hour. Work in a scratch repository, never in a real project.

## Before you start

- [ ] Install the `wm` being released, from the release branch or the built
      wheel, and check `wm --version`.
- [ ] Note the Claude Code version: `claude --version`.
- [ ] Make a scratch git repository with a little code in it (a small script and
      a test are enough), and commit it. Run `wm init`: nothing is staged,
      `git status` shows only `waymark/` and `.gitignore` as new, and
      `git config core.hooksPath` prints nothing. Run `wm doctor`: no errors.
- [ ] Commit `waymark/` and `.gitignore` as `chore: set up waymark`.
- [ ] **A fresh clone.** Clone the scratch repository into another folder and
      run `wm init` there: it sets up this machine and changes nothing in
      `waymark/`. `git status` is clean, and `wm doctor` has no errors. Delete
      the clone.

## Session start and kickoff

- [ ] Start Claude Code in the repository. Its first context includes the
      `wm status` view (ask the agent what the status says).
- [ ] Run `/wm-kickoff` and let it draft the charter. `wm check` passes.
- [ ] **Commit messages.** Ask the planner to stage something and run
      `git commit -m wip`. **The hook refuses it** with the reason, and nothing
      is committed. Ask it to commit again with a conventional message: the
      commit goes through.

## Propose and accept

- [ ] Run `/wm-propose` for a small change with **three** items: one untagged,
      and two tagged `build: delegate`. Its proposal has `Review: independent`.
      Not on the short path.
- [ ] Ask the agent to run `wm accept <change>`. **The hook refuses it**, and the
      agent tells you to run it yourself.
- [ ] Run `wm accept <change>` yourself.

## Apply and review

- [ ] Run `/wm-apply`. **The planner builds the untagged item itself**: it reads
      `wm context <change> <item> --for implement`, runs the checks the item
      touches and ticks the item with `wm tick`. It starts no implementer.
- [ ] For a tagged item, the planner starts the `wm-implementer` agent with a
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
- [ ] **The ending is recorded in the background (G46).** Claude Code runs
      agents in the background by default, and they hand their report back
      through `SubagentHandback`. Let the planner start an implementer as it
      chooses. When the implementer hands back its report, its `ITEM:` and
      `RESULT:` lines are recorded: the item is ticked in `tasks.md` without
      anyone running `wm tick`. The agent then stops without being asked for
      its ending again.
- [ ] **The ending is recorded in the foreground (G46).** Ask the planner to run
      the next implementer in the foreground and wait for it. When the
      implementer stops, the `ITEM:` and `RESULT:` lines in its final message are
      recorded: the item is ticked in `tasks.md` without anyone running
      `wm tick`.
- [ ] The planner commits each item's work with a conventional message once
      the item is ticked. No item gets a review of its own.
- [ ] Once every item is ticked, the planner starts the `wm-reviewer` agent
      with a prompt of exactly `<change>`. Ask it to start one with
      `<change> <item>` first: **the hook refuses it**.
- [ ] The reviewer reads `wm context <change> --for review`. Its verdict is
      written in the `## Log` section at the end of `tasks.md` as a
      `(review) <date> <verdict> by wm-reviewer` record in the reviewer's own
      words, with any `FINDING:` lines under it. The reviewer can't edit files (ask it to fix something; it is
      refused).
- [ ] **A request for changes.** If the reviewer asked for changes, the items
      it named are reopened, rebuilt and ticked, and the reviewer is started
      again. Otherwise record one yourself with
      `wm verdict <change> changes "<reasons>" --items <item>` and check that
      `wm instructions` reopens that item.

## Archive

- [ ] Before the review is recorded, try to archive: **refused**, naming the
      missing review of the change.
- [ ] Ask the agent to run `wm archive <change> --override "x"`. **Refused**.
- [ ] Run `/wm-archive` on the change's branch, before any pull request. The
      change moves to `changes/archive/<date>-<change>/`, the deltas are in the
      specs, and the proposal has an Outcome. The archive is committed on the
      branch.
- [ ] Run `wm pr <change>`: it describes the archived change, with its
      Outcome, and links to the proposal in the archived folder.
- [ ] `wm check` passes, and `wm status` shows the change as recently archived.

## The tiny path

- [ ] Ask for a typo fix in the scratch code with `/wm-fix`. The planner says
      why it changes no requirement and waits for your yes. It creates no change
      folder, commits with a conventional message, and offers a pull request.
      `wm status` shows no change in flight.
- [ ] Ask `/wm-fix` for something that changes a requirement. It says the work
      isn't tiny and hands over to `/wm-propose`.

## Atlas (when the release touches multi-repo)

- [ ] Make a scratch atlas and two code repos beside it. Run `wm init --atlas`,
      add the repos to the settings, `wm atlas register`, `wm atlas doctor`.
- [ ] **Attached folders (G57).** Start Claude Code in the atlas: it can read
      files in both code repos without `/add-dir`, from
      `.claude/settings.local.json`.
- [ ] **Hooks see those edits (G57).** An implementer's edit in the wrong code
      repo is refused; in its item's repo it is allowed.
- [ ] **The planner's edits.** While an untagged item that names one repo is
      being built, the planner's edit in that repo is allowed. Its edit in the
      other repo is refused, with a reason that names the repo it may edit now.

## Record the result

In the release's entry in `CHANGELOG.md`, add one line:

```
Smoke test: passed on <date> with Claude Code <version> on <operating system>.
```

List anything that failed and how it was fixed. In the README, replace the
"Claude Code version last verified" value with the version you tested.

# Lighter workflow

- Status: led-to [lighter-workflow](../milestones/archive/2026-11-15-lighter-workflow/goal.md)

## Context

Waymark is meant to be lightweight spec-driven development, but working on Waymark with it has felt slow, and the time and tokens don't match the size of the changes.

**What one change cost.** `drop-waymark-folder` (2026-11-15) ran 11 delegated agents, one after another. The figures below count sub-agent tokens only, not the planner's time or the two re-acceptances.

| | Runs | Tokens | Wall time |
|---|---|---|---|
| Implementers | 8 | ~775k | ~47 min |
| Reviewers | 3 | ~195k | ~7 min |
| Total | 11 | ~970k | ~56 min |

**Where the cost goes:**
- **Cold starts.** Every implementer and reviewer starts fresh and reads the charter, the proposal, the deltas, the design and the nearby code before doing anything. Items were small (1.3 was 29 lines), so the orientation costs more than the work.
- **The full suite runs about three times per item.** The implementer runs it, the independent reviewer runs it again, the planner runs targeted tests at self-review, and CI runs it once more. The charter's apply rule ("Run the full checks before reporting done") causes the first.
- **Fine-grained items.** The work was split into 8 items where about 4 would do, which means more cold starts, reviews and ticks.
- **Two PRs per change.** One for the code, and one for the archive, because archiving comes after the merge.
- **Reviewers found nothing to fix.** Across the 7 independent reviews so far, none found a bug. Implementers did wander: CRLF line endings, `Transaction.delete`, removing `config_value`. Those were reported or harmless.
- **Revisions withdraw acceptance.** That is right, but each added item cost a round trip to the human.
- **The short path is still heavy.** `check-release-pin`, about 30 lines in one tool, went through propose, accept, implement, review, PR, archive and an archive PR.

**The Fowler article.** "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl" (Birgitta Böckeler, martinfowler.com) lists these pitfalls, and they match Waymark as follows:

| Pitfall | Waymark |
|---|---|
| One workflow for every problem size ("a sledgehammer to crack a nut") | Partly: the short path drops only the design |
| Verbose markdown to review ("I'd rather review code than all these markdown files") | Yes: proposal, deltas, design and tasks; the design repeated the deltas |
| A false sense of control: agents don't follow every instruction | Mixed: implementers strayed in small ways, and reviewers mostly re-ran tests |
| Vague spec maintenance | Handled: deltas merge into living specs at archive. Nothing checks code against specs |
| Tension with small, iterative steps | Yes: the overhead per change discourages small changes |
| When to stay functional and when to get technical | Some drift: `setup` names `core.hooksPath` and `.gitignore` patterns |
| Non-determinism | Not applicable: code isn't regenerated from specs |

The article asks for workflows that scale with the size of the problem, a good experience for reviewing specs, and support for small iterative steps. Its closing question: "Are we making something worse in the attempt of making it better?"

**How OpenSpec does it.** This is from its `openspec-apply-change` and `openspec-verify-change` skills, `docs/customization.md` and `docs/workflows.md`, read on 2026-11-15.

| | OpenSpec | Waymark today |
|---|---|---|
| Who builds | The session agent, one task after another ("For each pending task… Keep going through tasks until done or blocked"), with no subagents. It stops when a task is unclear, when building it shows a design problem, when the work would go beyond the spec, or when something blocks it | A fresh implementer per item |
| Tests | Not in the skill. Left to the project's guidance, for example "Run focused tests before the full suite" | Every agent runs the full suite |
| Review | One optional verify per change, run by hand before archiving. It checks completeness (tasks done, each requirement implemented), correctness (each requirement and scenario covered) and coherence (the design is followed). Findings come back as CRITICAL, WARNING or SUGGESTION, with file and line. It is read-only and advisory, and doesn't block archiving | A self-review per item, or an independent reviewer agent per item |
| Approval | Informal: the human reviews the drafts and decides when to apply. No accept command | `wm accept`, fingerprinted, and withdrawn by any edit to the change |
| Evidence | The agent ticks its own boxes | Only `wm` writes ticks and verdicts, through the hooks |
| Scaling | By how clear the scope is: `/opsx:ff` drafts every artifact at once when the scope is known, and `/opsx:continue` drafts them one at a time. Every change still gets a folder | The short path drops the design |
| Project context | `openspec/config.yaml`: `context` (stack, conventions, constraints, injected into every artifact prompt), `rules.<artifact>` (only for that artifact), `operations.apply.guidance` and `operations.archive.guidance` (advisory), and `schema`. No vision, goals or glossary | A charter: vision, goals, non-goals, constraints, glossary, context, and rules per step |

OpenSpec is light because it trusts the agent and enforces nothing. Waymark's differences are an explicit approval and evidence that only `wm` writes. Both are cheap now that the hooks record results. Most of the cost comes from what OpenSpec never does: a cold agent for each item.

## Questions

- Should every item be built by a fresh agent from the record alone, or only large and risky ones? This decides between approaches A and B.
- Should tiny changes leave no trace in the record, or a one-line note such as a log entry or the changelog?
- Does the independent reviewer earn its cost? It found no bug in 7 reviews here, though it is meant for risky work.
- What counts as lightweight, in numbers? For example, a typical small change in under 10 minutes and under 100k tokens, from proposal to merge.
- Should specs hold only functional requirements, with files, settings and commands moved into the design?
- Can the archive go into the same PR as the code? That means archiving on the branch before the merge, while the human still decides when.
- Should the charter become a `context` and `[rules.<step>]` in `waymark/config.toml`, like OpenSpec's `config.yaml`? Vision, goals, non-goals and the glossary would then be dropped, or left to the README.
- Should review happen once per change, against the deltas' scenarios, instead of once per item?
- Should acceptance still be withdrawn when an item is only added, or only when what was accepted changes?

## Approaches

**A. Tune without changing the model.**
- Implementers run only the tests their item touches, and the full suite runs once, in CI.
- The planner plans fewer, larger items, one per coherent slice.
- Independent review is used only where a mistake is expensive.
- The archive is committed on the change's branch, so there is one PR per change.
- For: mostly charter rules and planner habits, so little code, and it can start now.
- Against: every item still starts cold, so the main cost stays.

**B. The planner builds by default, and delegation becomes the exception.**
- The planner already holds the context, so it builds items in the session.
- A fresh implementer is used only for items tagged for it, such as large or parallel work.
- The reviewer agent remains for `review: independent`.
- The record, the specs, acceptance and the evidence stay as they are.
- For: this removes most of the time and tokens.
- Against: it changes a core principle ("code is always built by an implementer, from the record alone"). "Agents only know what is written down" would then mean that the record is the source of truth, not that every edit comes from a cold agent. It also gives up the check that the record really is enough to build from.

**C. Paths that scale with size.**
- **Tiny** (typo, doc fix, small bug): no change folder, just a conventional commit. A spec line that changes goes through `wm sync`.
- **Small:** the short path, built by the planner, with one PR.
- **Full:** proposal, deltas, design and tasks, with delegation and independent review where they pay.
- The proposal names its path, and `wm check` holds each path to its rules.
- For: this answers the article's "one workflow for all sizes" head-on, and it combines with B.
- Against: more rules to learn, and the line between tiny and small has to be drawn clearly.

**D. OpenSpec's model, plus approval and evidence.**
- The planner builds items in the session, as in B. Tests are focused per item, and the full suite runs once before the PR.
- Review happens once per change, against the deltas' scenarios and the design, and reports findings by severity. A fresh reviewer agent runs it only for risky changes. Self-review otherwise.
- `wm accept` and evidence written only by `wm` stay.
- The charter folds into `waymark/config.toml`: its Context and Constraints become `context`, and its per-step Rules become `[rules.<step>]`. Vision, goals, non-goals and the glossary are dropped or left to the README. That removes one artifact from every project and shortens kickoff.
- For: a clear position, "OpenSpec plus recorded evidence and an approval gate". It cuts the per-item cost, and agents keep the same inputs.
- Against: the largest change of the four. It touches the skills, the agent definitions, the hooks' delegation gate, `wm instructions`, the context packs, kickoff and every doc, and existing charters need a migration.

**Alongside any of these: keep specs functional.** Requirements say what the system does. File names, settings and commands go in the design. Specs then churn less and are shorter to review.

## Conclusion

Decided on 2026-11-15: B and C together, with A's tactics. The planner builds by default and delegation becomes the exception. Review happens once per change, with an independent review only for risky changes. A tiny change is just a commit. The charter stays as it is: the project's context and its rules for agents are kept apart from the settings and atlas wiring in `waymark/config.toml`, so it is not folded into config. This continues as the milestone [lighter-workflow](../milestones/archive/2026-11-15-lighter-workflow/goal.md).

## Related

- Specs: `setup`, `agent-results`, `atlas`, `commits`
- Archived changes: `2026-11-15-keep-agent-setup-local`, `2026-11-15-record-background-agent-endings`, `2026-11-15-check-release-pin`, `2026-11-15-drop-waymark-folder`
- `docs/concepts.md`: the workflow, the roles, the review levels and the gates
- README, "What it costs", which promises time and token figures measured on Waymark itself
- Birgitta Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl", https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- OpenSpec: `skills/openspec-apply-change/SKILL.md`, `skills/openspec-verify-change/SKILL.md`, `docs/customization.md`, `docs/workflows.md`, https://github.com/Fission-AI/OpenSpec

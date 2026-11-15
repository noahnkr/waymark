# Lighter workflow

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

## Questions

- Should every item be built by a fresh agent from the record alone, or only large and risky ones? This decides between approaches A and B.
- Should tiny changes leave no trace in the record, or a one-line note such as a log entry or the changelog?
- Does the independent reviewer earn its cost? It found no bug in 7 reviews here, though it is meant for risky work.
- What counts as lightweight, in numbers? For example, a typical small change in under 10 minutes and under 100k tokens, from proposal to merge.
- Should specs hold only functional requirements, with files, settings and commands moved into the design?
- Can the archive go into the same PR as the code? That means archiving on the branch before the merge, while the human still decides when.

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

**Alongside any of these: keep specs functional.** Requirements say what the system does. File names, settings and commands go in the design. Specs then churn less and are shorter to review.

## Conclusion

## Related

- Specs: `setup`, `agent-results`, `atlas`, `commits`
- Archived changes: `2026-11-15-keep-agent-setup-local`, `2026-11-15-record-background-agent-endings`, `2026-11-15-check-release-pin`, `2026-11-15-drop-waymark-folder`
- `docs/concepts.md`: the workflow, the roles, the review levels and the gates
- README, "What it costs", which promises time and token figures measured on Waymark itself
- Birgitta Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl", https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html

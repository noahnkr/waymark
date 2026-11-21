# Review

## Purpose

How a change is checked before it is archived: one review of the whole change at the change's review level, how it is recorded with its findings, what a request for changes reopens, and what goes to the human.

## Requirements

### Requirement: Review level per change
A change's review level SHALL be the value of the `- **Review:**` line in its proposal: `self`, `independent` or `none`. `wm new change` SHALL write the line under the Owner line, holding the project's `default_review`, or `self` on the short path when the default is `independent`. On the short path the level SHALL be `self` or `none`. `wm check` SHALL report as an error an active change whose proposal has no Review line, an unknown value, or `independent` on the short path. It SHALL warn when the change's deltas modify or remove a requirement and the level isn't `independent`.

#### Scenario: Level from the proposal
- GIVEN a project whose `default_review` is `self`
- WHEN a change's proposal has the line `- **Review:** independent`
- THEN `wm show <change>` gives the review level `independent`

#### Scenario: Default written at creation
- GIVEN a project whose `default_review` is `independent`
- WHEN the planner runs `wm new change add-limit`
- THEN the proposal has the line `- **Review:** independent` under its Owner line

#### Scenario: Default on the short path
- GIVEN a project whose `default_review` is `independent`
- WHEN the planner runs `wm new change add-limit --short`
- THEN the proposal has the line `- **Review:** self`

#### Scenario: Review line missing
- GIVEN an active change whose proposal has no `- **Review:**` line
- WHEN `wm check` runs
- THEN it reports an error on the proposal that shows the line `- **Review:** <level>` to add

#### Scenario: Risky change at self
- GIVEN a change whose deltas modify a requirement and whose review level is `self`
- WHEN `wm check` runs
- THEN it warns that a change that modifies or removes a requirement should be reviewed independently

### Requirement: One review per change
When every item of an accepted change is ticked and the change isn't reviewed, `wm instructions` SHALL make the next step a review of the whole change. At `self` the planner records it. At `independent` a reviewer agent is started with the change's name and nothing else. At `none` no review is needed.

#### Scenario: All items ticked
- GIVEN an accepted change at review level `self` with every item ticked and no review recorded
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is the review of the change, and the command is `wm review <change> --self "<summary>"`

#### Scenario: An item still to build
- GIVEN an accepted change with item 1.1 ticked and item 1.2 not ticked
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step is to apply item 1.2, not a review

### Requirement: Review recorded in the task list
`wm` SHALL write the review of a change as a `(review)` or `(self-review)` record in the `## Log` section at the end of the change's task list, creating the section if needed. It SHALL write each finding under its record as a sub-line with a severity in brackets (`[critical]`, `[warning]` or `[suggestion]`), its place in backticks, and a text, and then each detail as a sub-line without a severity. A sub-line under a review that starts with a severity in brackets SHALL be read as a finding, one that starts with a severity word followed by `:` or by a place in backticks SHALL be reported as a finding written without its brackets, and any other SHALL be read as a detail. It SHALL refuse a `pass` verdict, or a self-review, that comes with a critical finding.

#### Scenario: Self-review with a finding
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "<summary>" --finding "warning: src/a.py:12: <text>"`
- THEN the task list ends with a `## Log` section holding a `(self-review)` record with the summary and, under it, ``- [warning] `src/a.py:12`: <text>``

#### Scenario: Self-review with a finding and details
- GIVEN an accepted change at review level `self` with every item ticked
- WHEN the planner runs `wm review <change> --self "every criterion holds" --finding "suggestion: src/a.py: name the constant" --detail "pytest passes" --detail "wm check is healthy"`
- THEN under the `(self-review)` record come ``- [suggestion] `src/a.py`: name the constant``, then `- pytest passes`, then `- wm check is healthy`

#### Scenario: Pass with a critical finding
- GIVEN a change waiting for an independent review
- WHEN a `pass` verdict comes with a `critical` finding
- THEN it is refused with the reason, and nothing is written

### Requirement: Changes reopen the named items
A `changes` verdict SHALL name the items to rebuild, and `wm` SHALL refuse one that names none, or names an item the change doesn't have. The record SHALL list them as `changes <item>, <item>...`, ending with `;` when `covers` follows. The named items SHALL be the next to apply, each reopened with `wm reopen`. Once they are ticked again, the change SHALL need an independent review, whatever its level.

#### Scenario: Two items named
- GIVEN a change at review level `self` with items 1.1, 1.2 and 2.1 ticked
- WHEN a verdict of `changes` naming items 1.2 and 2.1 is recorded on 2026-11-20
- THEN the Log holds `2026-11-20 (review) changes 1.2, 2.1; covers 1.1, 1.2, 2.1 by <who>: <reasons>`, the next step is to reopen and apply item 1.2, then item 2.1, and once both are ticked again the next step is an independent review

### Requirement: Escalation to the human
A second `changes` verdict on a change, or a `spec-gap` verdict, SHALL send the change to the human: it appears in `wm inbox`, and no step is offered to the planner until the human's decision is recorded with `wm resolve <change> "<what was decided>"`.

#### Scenario: Second request for changes
- GIVEN a change with one `changes` verdict whose named items have been rebuilt
- WHEN a second `changes` verdict is recorded
- THEN `wm inbox` lists the change with the verdict's reasons, and `wm instructions` names no step for the planner

### Requirement: Archive needs the change's review
`wm archive` SHALL refuse a change that needs a review and has no passing one, unless the human overrides it with a reason. The override SHALL be written as an `(override)` record in the change's Log, and `wm pr` SHALL show it. A change at level `none` SHALL need no review.

#### Scenario: Not reviewed
- GIVEN a change at review level `self` with every item ticked and no review
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names the missing review

#### Scenario: Overridden
- GIVEN a change at review level `self` with every item ticked and no review
- WHEN the human runs `wm archive <change> --override "<reason>"`
- THEN the archived change's Log holds an `(override)` record with the reason, and `wm pr` shows it

### Requirement: Review of items added after a review
Every `(review)` and `(self-review)` record SHALL name the items it covers, as `covers <item>, <item>...` before who wrote it; `wm` SHALL write every item of the change at the time, or the items that review was of. A record without `covers` SHALL cover every item. A review SHALL NOT cover an item reopened after it: a passing review counts for an item only when no `(reopened)` record for that item follows the review. When every item is ticked and some item is covered by no passing review or self-review, `wm instructions` SHALL make the next step a review of those items only, at the change's level, and the record it writes SHALL cover just them. `wm archive` SHALL refuse such a change unless the human overrides it with a reason, as it refuses an unreviewed one.

#### Scenario: Item added after a pass
- GIVEN an accepted change at review level `independent` whose items 1.1 and 1.2 passed a review covering them
- WHEN item 1.3 is added, built and ticked
- THEN the next step is a review of item 1.3 only, the reviewer can be started with the change's name, and its passing verdict is written as `<date> (review) pass covers 1.3 by reviewer: <reasons>`

#### Scenario: Item reopened after a pass
- GIVEN an accepted change at review level `self` whose items 1.1 and 1.2 passed a self-review covering them
- WHEN item 1.2 is reopened with `--reason`, built again and ticked
- THEN the next step is a review of item 1.2 only

#### Scenario: Archive before the added item is reviewed
- GIVEN the same change with item 1.3 ticked and no review covering it
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names item 1.3 as not reviewed

#### Scenario: Older review records
- GIVEN an archived change whose review record has no `covers`
- WHEN `wm show <change>` runs
- THEN the review is shown as covering every item, and nothing is reported missing

### Requirement: Human items in a review
When a change has items with `- **Build:** human`, `wm instructions` at its review step and `wm context <change> --for review` SHALL name those items and say that each one's tick is the human's confirmation of what only they could check. The review SHALL take that confirmation as given and SHALL still check anything the item left in the repo, such as a resource it updated.

#### Scenario: Human item in the review pack
- GIVEN an accepted change at review level `independent` whose items are all ticked, item 1.2 having `- **Build:** human`
- WHEN the reviewer runs `wm context <change> --for review`
- THEN the pack names item 1.2 as done by the human, and says its tick is the human's confirmation and that what it left in the repo is still checked

#### Scenario: Self-review with a human item
- GIVEN an accepted change at review level `self` whose items are all ticked, item 1.2 having `- **Build:** human`
- WHEN the planner runs `wm instructions --change <change>`
- THEN the review guidance names item 1.2 as done by the human and says its tick is the human's confirmation

### Requirement: Reopening a ticked item
`wm reopen <change> <item> --reason "<why>"` SHALL reopen a ticked item of an accepted change that no open review names: it SHALL take the item's tick off and write a `(reopened)` record naming the item, with the reason as its text. Without `--reason`, it SHALL refuse such an item, with a reason that names `--reason`. It SHALL refuse an item that isn't ticked, and a change that isn't accepted. An item an open review names SHALL be reopened as before, `--reason` being optional for it. Reopening SHALL NOT withdraw acceptance.

#### Scenario: Ticked item reopened with a reason
- GIVEN an accepted change with item 2.3 ticked, no open review naming it, and a git user named Ada
- WHEN the planner runs `wm reopen <change> 2.3 --reason "its criteria changed"` on 2026-11-20
- THEN item 2.3 is not ticked, the Log ends with `2026-11-20 (reopened) 2.3 by planner for Ada: its criteria changed`, the change is still accepted, and `wm instructions` offers item 2.3 to apply

#### Scenario: No reason given
- GIVEN an accepted change with item 2.3 ticked and no open review naming it
- WHEN the planner runs `wm reopen <change> 2.3`
- THEN it is refused with a reason that names `--reason`, and nothing is written

#### Scenario: Item not ticked
- GIVEN an accepted change with item 2.3 not ticked
- WHEN the planner runs `wm reopen <change> 2.3 --reason "<why>"`
- THEN it is refused with a reason that says item 2.3 isn't ticked, and nothing is written

### Requirement: Revised item reopened before review
When an accepted change has an item that a `(revised)` record names while its Log shows it ticked, and no later `(ticked)`, `(reopened)` or item `(resolved)` record for it follows, `wm instructions` SHALL make the next step reopening and applying that item, with `wm reopen <change> <item> --reason "<what the revision changed>"` first among its commands, before any review or archive. Only a review that went to the human SHALL come before it. `wm archive` SHALL refuse such a change, naming the item, and the refusal SHALL NOT be overridable.

#### Scenario: Revised item is the next step
- GIVEN an accepted change with items 1.1 and 1.2 ticked, whose item 1.2 was then revised with `wm revise <change> "<why>" --parts 1.2`, and the change accepted again
- WHEN the planner runs `wm instructions --change <change>`
- THEN the step applies item 1.2, and its first command is `wm reopen <change> 1.2 --reason "<what the revision changed>"`

#### Scenario: Archive refused for a revised item
- GIVEN the same change, with every item ticked and a passing review recorded before the revision
- WHEN `wm archive <change> --override "<reason>"` runs
- THEN it is refused with a reason that names item 1.2 and `wm reopen`, and nothing is written

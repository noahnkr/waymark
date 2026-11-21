# Review

## ADDED Requirements

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

## MODIFIED Requirements

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

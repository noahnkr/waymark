# Review

## ADDED Requirements

### Requirement: Review of items added after a review
Every `(review)` and `(self-review)` record SHALL name the items it covers, as `covers <item> <item>...` before who wrote it; `wm` SHALL write every item of the change at the time, or the items that review was of. A record without `covers` SHALL cover every item. When every item is ticked and some item is covered by no passing review or self-review, `wm instructions` SHALL make the next step a review of those items only, at the change's level, and the record it writes SHALL cover just them. `wm archive` SHALL refuse such a change unless the human overrides it with a reason, as it refuses an unreviewed one.

#### Scenario: Item added after a pass
- GIVEN an accepted change at review level `independent` whose items 1.1 and 1.2 passed a review covering them
- WHEN item 1.3 is added, built and ticked
- THEN the next step is a review of item 1.3 only, the reviewer can be started with the change's name, and its passing verdict is written as `(review) <date> pass covers 1.3 by wm-reviewer: <reasons>`

#### Scenario: Archive before the added item is reviewed
- GIVEN the same change with item 1.3 ticked and no review covering it
- WHEN `wm archive <change>` runs without an override
- THEN it is refused, and the reason names item 1.3 as not reviewed

#### Scenario: Older review records
- GIVEN an archived change whose review record has no `covers`
- WHEN `wm show <change>` runs
- THEN the review is shown as covering every item, and nothing is reported missing

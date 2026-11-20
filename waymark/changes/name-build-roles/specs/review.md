# Review

## ADDED Requirements

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

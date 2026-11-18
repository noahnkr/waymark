# Skills

## ADDED Requirements

### Requirement: Resuming an exploration
The `wm-explore` skill SHALL resume a saved exploration when it is started with an active exploration's name, or when the idea matches an active exploration and the human confirms it is that one. It SHALL read the exploration with `wm show`, tell the human what in the record has changed that bears on it since it was written, such as specs, changes in flight and archived changes it touches, and continue from the exploration's Questions and Approaches rather than from a blank page.

#### Scenario: Started with an exploration's name
- GIVEN the installed `wm-explore` skill
- WHEN its steps are read
- THEN a first step reads a named active exploration with `wm show`, reports what in the record changed since, and continues from its Questions and Approaches

## MODIFIED Requirements

### Requirement: Explore's closing offers
The `wm-explore` skill SHALL close with four offers. For a new idea: do nothing, save an exploration, start a proposal of any size with `wm-propose`, or start a milestone. For a resumed exploration: do nothing, leaving it open; update it, revising its sections or dropping it with `wm exploration drop`; start a proposal with `wm-propose`; or start a milestone. When the work comes from a saved exploration, the change SHALL be created with `wm new change --from <exploration>` and the milestone with `wm new milestone --from <exploration>`, and neither skill SHALL write an exploration's Status line by hand.

#### Scenario: No tiny-path offer
- GIVEN the installed `wm-explore` skill
- WHEN its closing offers are read
- THEN there are four, and none names `wm-fix`

#### Scenario: Offers for a resumed exploration
- GIVEN the installed `wm-explore` skill
- WHEN its closing offers for a resumed exploration are read
- THEN there are four: do nothing, update or drop it with `wm exploration drop`, a proposal, and a milestone with `--from`

#### Scenario: Proposal from an exploration
- GIVEN the installed `wm-propose` skill
- WHEN its naming step is read
- THEN it passes `--from <exploration>` to `wm new change` when the work comes from a saved exploration

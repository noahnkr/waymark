# Step guidance

## MODIFIED Requirements

### Requirement: Writing and sizing rules
`wm instructions` for the specs step SHALL give, in its guidance, the rules for writing requirements:
- one behavior per requirement, stated in a sentence or two with SHALL;
- what a user or another program sees, not how it is built;
- a scenario for the usual case, and one for each refusal or boundary the requirement names;
- each scenario's WHEN is one action, and its THEN an outcome someone else can check, quoting exact output where it matters.

`wm instructions` for the tasks step SHALL give, in its guidance, the rules for sizing items:
- one item per slice that can be built and verified on its own;
- an item whose criteria run past about five bullets, or that spans unrelated parts of the code, is split;
- docs and skills a change makes stale get their own item;
- a change that sets up or alters something outside the repo gets an item to create or update its resource;
- items come in an order where the record stays healthy after each is ticked.

#### Scenario: Specs step
- GIVEN a change whose next step is specs
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN its guidance holds the rule that each THEN is an outcome someone else can check

#### Scenario: Tasks step
- GIVEN a change whose next step is tasks
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN its guidance holds the rule that an item whose criteria run past about five bullets is split

#### Scenario: Resource item
- GIVEN a change whose next step is tasks
- WHEN the planner runs `wm instructions --change <change> --json`
- THEN its guidance holds the rule that a change that alters something outside the repo gets an item to create or update its resource

# Authored formats

## ADDED Requirements

### Requirement: Spec background
A spec MAY have a `## Background` section, after its Purpose and before its Requirements, holding the facts about its area that aren't requirements. A delta MAY have a `## Background` section; archiving or syncing the change SHALL set the spec's Background to the delta's, whole, adding the section when the spec has none. `wm check` SHALL report as an error an empty Background section in a spec or a delta.

#### Scenario: Background set by a delta
- GIVEN a spec `lead-nurture` with no Background, and a change whose delta for it has a Background holding "Leads come from A Place for Mom."
- WHEN the change is archived
- THEN the spec has a `## Background` section after its Purpose holding "Leads come from A Place for Mom.", and its requirements are unchanged

#### Scenario: Background replaced
- GIVEN a spec whose Background holds "Leads come from A Place for Mom.", and a change whose delta's Background holds "Leads come from A Place for Mom and Caring.com."
- WHEN the change is archived
- THEN the spec's Background holds only "Leads come from A Place for Mom and Caring.com."

#### Scenario: Empty background
- GIVEN an active change whose delta has a `## Background` heading with nothing under it
- WHEN `wm check` runs
- THEN it reports an error on that heading that says the Background is empty

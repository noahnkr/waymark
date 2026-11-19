# <Spec title>

<!-- One file per spec this change touches: specs/<domain>.md inside the change.
     Keep only the sections you need. A requirement's heading is its key.
     Good requirement: "A search SHALL return at most fifty results, best matches
     first", with a scenario whose THEN can be checked.
     Bad requirement: "The SearchService caps results in cut_list()". It names
     internals, which belong in the design. -->

## Purpose

<!-- Only when this delta creates the spec, or changes what the spec is for.
     Otherwise remove this section. -->

## Background

<!-- Facts about this spec's area that aren't requirements and can't be found in
     the code. This section replaces the spec's Background whole.
     Good: "Leads come from A Place for Mom, one email per lead."
     Bad: "The funnel SHALL answer a new lead within an hour." It says what the
     system does, so it is a requirement.
     Remove this section unless the change sets the Background. -->

## ADDED Requirements

### Requirement: <name>
<What the system SHALL do, in one statement.>

#### Scenario: <name>
- GIVEN <a starting state>
- WHEN <something happens>
- THEN <the outcome that can be checked>

## MODIFIED Requirements

<!-- Write each requirement out in full, as it should read afterwards, under the
     heading it has in the spec, or under its new name when this delta also renames it. -->

## REMOVED Requirements

### Requirement: <name>
**Reason:** <why it goes>

## RENAMED Requirements

- **From:** <old name>
- **To:** <new name>

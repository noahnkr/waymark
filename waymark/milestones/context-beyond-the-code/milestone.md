# Context beyond the code

## Goal

Give every fact an agent needs, and can't find in the code or in the requirements, one place in the record, and get it to the agents whose work it bears on. What applies to the whole project lives in the charter: its context, and one numbered list of rules. What applies to one area of the project lives with that area's spec, in a Background section. What describes the world outside the repo, such as the services, platforms, accounts, databases, datasets and documents a project depends on, lives in resources. This makes Waymark fit projects like shs-nexus, an internal platform built on a small business's outside tools, as well as it fits Waymark itself.

## Done when

- A resource holds the as-built facts about one thing outside the repo, in one layout for every kind, edited by hand like a doc, and `wm check` holds it to its layout and the specs it serves.
- The charter's Rules are one numbered list, given to every agent at every step, and this repository's charter is written that way.
- A spec may have a Background section, changed through a delta like its Purpose and requirements.
- The implement and review packs carry the Background of every spec the change touches, and a summary of each active resource that serves one; the explore pack indexes the resources.

## Non-goals

- A standalone decision log or question notes; decisions stay in designs.
- A staleness warning for resources, or a scan for secrets in them.
- Reading another atlas's resources or Background.
- Converting shs-nexus's existing vault to Waymark.

## Roadmap

- [add-resources](../../changes/archive/2026-11-18-add-resources/proposal.md): resources in `waymark/resources/`, with six fixed sections and the lines Kind, Serves, Status and Verified; `wm new resource <name> <kind>`, `wm ls resources` and `wm show --kind resource`; edited by hand, including by implementers and as tiny work; summarized in the implement and review packs of a change that touches a spec they serve
- flatten-charter-rules: the charter's Rules become one numbered list, given whole to every step's instructions and every context pack, in place of step headings
- [add-spec-background](../../changes/archive/2026-11-18-add-spec-background/proposal.md): a spec may have a `## Background` section of facts for its area, changed through a delta, and carried in the implement and review packs of a change that touches the spec

## Log

- (proposed) 2026-11-17 add-resources by Noah Roberts
- (archived) 2026-11-18 add-resources by Noah Roberts
- (archived) 2026-11-18 add-spec-background by Noah Roberts

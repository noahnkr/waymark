# Lighter workflow: roadmap

- planner-builds: the planner builds items in the session; `delegate` tags the items that go to a fresh implementer; focused tests per item and the full checks once before the PR (the charter's apply rule changes)
- review-per-change: one review per change against the deltas' scenarios, with findings by severity; independent only for risky changes
- archive-before-merge: archive on the change's branch so code and archive share one PR
- size-paths: tiny, short and full paths, named in the proposal and held by `wm check`; specs stay functional
- accept-on-change: adding an item no longer withdraws acceptance; changing what was accepted still does
- charter-into-config: fold the charter's context and rules into `waymark/config.toml`, with a migration (last, and only if the rest leaves it worth doing)

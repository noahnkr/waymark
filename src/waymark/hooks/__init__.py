"""Hook decisions: what an agent may do, decided once, for every agent tool.

An adapter translates its tool's hook events into the neutral events here and
translates the decisions back. Every rule lives on this side, so behavior
can't drift between tools.
"""

"""The record model: the only code that reads or writes the record's files.

It finds the project, parses every artifact, derives state from the files and
git, merges deltas into specs, and validates links.
"""

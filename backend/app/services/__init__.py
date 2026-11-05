"""Business services (changes, audit, numbering, reports). mypy --strict.

Every service function that modifies data must call audit.record(...) in the same
transaction (CLAUDE.md 6.2).
"""

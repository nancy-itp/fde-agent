"""Parameterized SQLAlchemy queries for the Review Workflow service.

Not yet implemented — see `service.py`'s docstring for scope and phase.
`MismatchFlag` writes/reads (this service's model, `models.py`) belong here
once the review queue is built; so does the append-only audit log table
CLAUDE.md §7 requires (not yet designed/migrated — a separate table from
`MismatchFlag`, which is the current-state record, not the audit trail).
"""

from __future__ import annotations

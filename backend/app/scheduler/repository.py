"""Parameterized SQLAlchemy queries for the Scheduler service.

Not yet implemented — see `service.py`'s docstring for scope and phase.
`ReviewCycle` (this service's model, `models.py`) already has one reader:
`app.employee_profile.repository.get_current_open_cycle`. That query stays
there for now (it's a read employee_profile needs, not scheduler business
logic) rather than being moved here speculatively.
"""

from __future__ import annotations

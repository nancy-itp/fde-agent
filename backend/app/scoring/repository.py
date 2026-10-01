"""Parameterized SQLAlchemy queries for the Scoring service.

Not yet implemented — see `service.py`'s docstring for scope and phase.
`PerformanceScore` writes must be keyed on `(employee_id, cycle_id,
dimension_name)` per `docs/ARCHITECTURE.md`'s idempotency requirement, so a
retried partial scoring pass never double-writes a dimension.
`employee_profile.repository.list_scores_for_cycle` already reads
`PerformanceScore` (this service's model) for the employee dashboard — that
stays there; it's a read employee_profile needs, not scoring business
logic.
"""

from __future__ import annotations

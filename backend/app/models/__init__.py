"""Re-export aggregator, not a model-owning package.

Every model's canonical definition lives in its owning service's
`models.py` (per CLAUDE.md §2 — one module per Core Application Service).
This module exists only so `alembic/env.py` can do `from app.models import *`
and have every table registered on `Base.metadata` in one place, without
each migration needing to know which service owns which model.

Import models from their owning service directly in new code
(`from app.scoring.models import PerformanceScore`, not
`from app.models import PerformanceScore`) — this module is infrastructure
for Alembic, not a service to depend on.
"""

from app.employee_profile.models import (
    Availability,
    Employee,
    EmployeeAvailabilityStatus,
    EmployeeRole,
    SelfReport,
)
from app.prio_integration.models import PrioSnapshot
from app.review_workflow.models import MismatchFlag
from app.scheduler.models import ReviewCycle, ReviewCycleStatus
from app.scoring.models import ApiCallLog, ApiCallStatus, ApiCallType, PerformanceScore

__all__ = [
    "ApiCallLog",
    "ApiCallStatus",
    "ApiCallType",
    "Availability",
    "Employee",
    "EmployeeAvailabilityStatus",
    "EmployeeRole",
    "MismatchFlag",
    "PerformanceScore",
    "PrioSnapshot",
    "ReviewCycle",
    "ReviewCycleStatus",
    "SelfReport",
]

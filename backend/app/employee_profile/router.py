"""HTTP routes for the Employee/Profile Management service.

Every route resolves the caller from `get_current_employee` (the verified
JWT) and passes only that employee_id into the service layer — there is no
client-suppliable employee_id anywhere on this router, so cross-employee
access isn't just discouraged, it's structurally impossible from this
surface (see docs/ARCHITECTURE.md's row-level-access pattern).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_employee
from app.employee_profile import service
from app.employee_profile.schemas import (
    AvailabilityOut,
    AvailabilityUpdateIn,
    EmployeeProfileOut,
    PerformanceScoreOut,
    ReviewCycleOut,
)

router = APIRouter(tags=["employee-profile"])


@router.get("/employees/me", response_model=EmployeeProfileOut)
def get_my_profile(
    current_user: CurrentUser = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeProfileOut:
    """Return the caller's own employee profile."""
    employee = service.get_own_profile(db, current_user.employee_id)
    return EmployeeProfileOut.model_validate(employee)


@router.get("/employees/me/availability", response_model=AvailabilityOut)
def get_my_availability(
    current_user: CurrentUser = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    """Return the caller's own availability record."""
    availability = service.get_own_availability(db, current_user.employee_id)
    return AvailabilityOut.model_validate(availability)


@router.patch("/employees/me/availability", response_model=AvailabilityOut)
def update_my_availability(
    payload: AvailabilityUpdateIn,
    current_user: CurrentUser = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    """Update the caller's own self-reported availability/skills fields."""
    availability = service.update_own_availability(db, current_user.employee_id, payload)
    return AvailabilityOut.model_validate(availability)


@router.get("/employees/me/scores", response_model=list[PerformanceScoreOut])
def get_my_scores(
    cycle_id: int | None = None,
    current_user: CurrentUser = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[PerformanceScoreOut]:
    """Return the caller's own performance scores, defaulting to the current cycle."""
    scores = service.get_own_scores(db, current_user.employee_id, cycle_id)
    return [PerformanceScoreOut.model_validate(score) for score in scores]


@router.get("/cycles/current", response_model=ReviewCycleOut)
def get_current_cycle(
    _current_user: CurrentUser = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ReviewCycleOut:
    """Return the current open review cycle.

    Temporary home for this read — moves into a `review_workflow` module
    once that service exists.
    """
    cycle = service.get_current_cycle(db)
    return ReviewCycleOut.model_validate(cycle)

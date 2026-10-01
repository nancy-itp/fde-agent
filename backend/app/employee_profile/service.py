"""Business logic for the Employee/Profile Management service.

Routes call into here; this is the only layer that talks to `repository.py`.
Every function takes the caller's own employee_id (from the verified JWT,
never client-supplied) and scopes every read/write to it.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.employee_profile import repository
from app.employee_profile.models import Availability, Employee
from app.employee_profile.schemas import AvailabilityUpdateIn
from app.scheduler.models import ReviewCycle
from app.scoring.models import PerformanceScore


def get_own_profile(db: Session, employee_id: int) -> Employee:
    employee = repository.get_employee(db, employee_id)
    if employee is None:
        raise NotFoundError("Employee profile not found.")
    return employee


def get_own_availability(db: Session, employee_id: int) -> Availability:
    availability = repository.get_availability(db, employee_id)
    if availability is None:
        raise NotFoundError("Availability record not found.")
    return availability


def update_own_availability(db: Session, employee_id: int, payload: AvailabilityUpdateIn) -> Availability:
    return repository.update_availability(
        db,
        employee_id,
        available=payload.available,
        skill_set=payload.skill_set,
        availability_status=payload.availability_status,
        skills=payload.skills,
    )


def get_current_cycle(db: Session) -> ReviewCycle:
    cycle = repository.get_current_open_cycle(db)
    if cycle is None:
        raise NotFoundError("No review cycle is currently open.")
    return cycle


def get_own_scores(db: Session, employee_id: int, cycle_id: int | None) -> list[PerformanceScore]:
    resolved_cycle_id = cycle_id
    if resolved_cycle_id is None:
        resolved_cycle_id = get_current_cycle(db).cycle_id
    return repository.list_scores_for_cycle(db, employee_id, resolved_cycle_id)

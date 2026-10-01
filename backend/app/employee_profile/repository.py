"""Parameterized SQLAlchemy queries for the Employee/Profile Management service.

No business logic here — that belongs in service.py. This layer is the only
place that talks to the SQLAlchemy session for this service.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.employee_profile.models import Availability, Employee, EmployeeAvailabilityStatus
from app.scheduler.models import ReviewCycle, ReviewCycleStatus
from app.scoring.models import PerformanceScore


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def get_active_employee(db: Session, employee_id: int) -> Employee | None:
    employee = db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        return None
    return employee


def get_availability(db: Session, employee_id: int) -> Availability | None:
    return db.get(Availability, employee_id)


def update_availability(
    db: Session,
    employee_id: int,
    *,
    available: bool | None,
    skill_set: str | None,
    availability_status: EmployeeAvailabilityStatus | None,
    skills: str | None,
) -> Availability:
    """Update only employee-self-reported fields; staffing fields are untouched."""
    availability = db.get(Availability, employee_id)
    if availability is None:
        availability = Availability(employee_id=employee_id, available=available if available is not None else True)
        db.add(availability)

    if available is not None:
        availability.available = available
    if skill_set is not None:
        availability.skill_set = skill_set

    employee = db.get(Employee, employee_id)
    if employee is not None:
        if availability_status is not None:
            employee.availability_status = availability_status
        if skills is not None:
            employee.skills = skills

    db.commit()
    db.refresh(availability)
    return availability


def list_scores_for_cycle(db: Session, employee_id: int, cycle_id: int) -> list[PerformanceScore]:
    stmt = select(PerformanceScore).where(
        PerformanceScore.employee_id == employee_id,
        PerformanceScore.cycle_id == cycle_id,
    )
    return list(db.scalars(stmt))


def get_cycle(db: Session, cycle_id: int) -> ReviewCycle | None:
    return db.get(ReviewCycle, cycle_id)


def get_current_open_cycle(db: Session) -> ReviewCycle | None:
    stmt = (
        select(ReviewCycle)
        .where(ReviewCycle.status == ReviewCycleStatus.OPEN)
        .order_by(ReviewCycle.cycle_start.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()

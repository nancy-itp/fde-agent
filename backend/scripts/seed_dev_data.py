"""Dev-only seed data so the Employee Dashboard has something real to render.

Not for staging/production use — inserts synthetic employees, an open
review cycle, and a few performance_scores rows. Safe to re-run: it upserts
by primary key rather than blindly inserting duplicates.

Usage (from backend/):
    python -m scripts.seed_dev_data
"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import (
    Availability,
    Employee,
    EmployeeAvailabilityStatus,
    EmployeeRole,
    PerformanceScore,
    ReviewCycle,
    ReviewCycleStatus,
)

DIMENSIONS = [
    ("Technical fundamentals & application", 82.0, 0.8),
    ("Practical execution / delivery", 91.0, 0.95),
    ("Troubleshooting & problem-solving", 75.0, 0.9),
    ("Communication & proactive escalation", 68.0, None),
    ("Documentation habits", 60.0, 0.7),
    ("Ownership & reliability", 88.0, 0.92),
]


def seed(db) -> None:
    manager = db.get(Employee, 1) or Employee(employee_id=1)
    manager.name = "Priya Manager"
    manager.email = "priya.manager@example.com"
    manager.role = EmployeeRole.MANAGER
    manager.is_active = True
    db.add(manager)
    db.flush()

    employees = []
    for employee_id, name, email in (
        (2, "Alex Employee", "alex.employee@example.com"),
        (3, "Sam Employee", "sam.employee@example.com"),
    ):
        employee = db.get(Employee, employee_id) or Employee(employee_id=employee_id)
        employee.name = name
        employee.email = email
        employee.role = EmployeeRole.EMPLOYEE
        employee.manager_id = manager.employee_id
        employee.is_active = True
        employee.skills = "Python, SQL, FastAPI"
        employee.availability_status = EmployeeAvailabilityStatus.AVAILABLE
        db.add(employee)
        employees.append(employee)
    db.flush()

    for employee in employees:
        availability = db.get(Availability, employee.employee_id) or Availability(
            employee_id=employee.employee_id
        )
        availability.available = True
        availability.skill_set = employee.skills
        availability.client_name = "Acme Corp"
        availability.project_name = "Platform Modernization"
        availability.allocation_percent = 80.0
        db.add(availability)

    cycle = db.get(ReviewCycle, 1) or ReviewCycle(cycle_id=1)
    cycle.cycle_start = date.today() - timedelta(days=14)
    cycle.cycle_end = date.today()
    cycle.status = ReviewCycleStatus.OPEN
    db.add(cycle)
    db.flush()

    existing_score_ids = {
        score_id
        for (score_id,) in db.query(PerformanceScore.score_id).filter(
            PerformanceScore.cycle_id == cycle.cycle_id
        )
    }
    next_score_id = max(existing_score_ids, default=0) + 1
    for employee in employees:
        already_scored = db.query(PerformanceScore).filter_by(
            employee_id=employee.employee_id, cycle_id=cycle.cycle_id
        ).count()
        if already_scored:
            continue
        for dimension_name, score, confidence in DIMENSIONS:
            db.add(
                PerformanceScore(
                    score_id=next_score_id,
                    employee_id=employee.employee_id,
                    cycle_id=cycle.cycle_id,
                    dimension_name=dimension_name,
                    score=score,
                    confidence=confidence,
                )
            )
            next_score_id += 1

    db.commit()


def main() -> None:
    if settings.environment != "development":
        raise SystemExit("Refusing to seed: ENVIRONMENT is not 'development'.")
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    print("Seed complete: employees 1 (manager), 2 and 3 (employees), cycle 1 (open), scores.")


if __name__ == "__main__":
    main()

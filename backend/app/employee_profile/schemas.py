"""Request/response schemas for the Employee/Profile Management service."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.employee_profile.models import EmployeeAvailabilityStatus, EmployeeRole
from app.scheduler.models import ReviewCycleStatus


class EmployeeProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    name: str
    email: str
    role: EmployeeRole
    skills: str | None
    availability_status: EmployeeAvailabilityStatus | None


class AvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    available: bool
    skill_set: str | None
    client_name: str | None
    project_name: str | None
    allocation_percent: float | None


class AvailabilityUpdateIn(BaseModel):
    """Only the fields an employee may self-report.

    `client_name`/`project_name`/`allocation_percent` are staffing
    assignments set elsewhere and are intentionally not part of this schema.
    """

    available: bool | None = None
    skill_set: str | None = Field(default=None, max_length=1000)
    availability_status: EmployeeAvailabilityStatus | None = None
    skills: str | None = Field(default=None, max_length=1000)


class ReviewCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycle_id: int
    cycle_start: date
    cycle_end: date
    status: ReviewCycleStatus


class PerformanceScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score_id: int
    cycle_id: int
    dimension_name: str
    score: float
    confidence: float | None

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import AuditMixin


class EmployeeRole(enum.StrEnum):
    EMPLOYEE = "Employee"
    MANAGER = "Manager"
    ADMIN = "Admin"


class EmployeeAvailabilityStatus(enum.StrEnum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    PARTIALLY_AVAILABLE = "PartiallyAvailable"


class Employee(Base, AuditMixin):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[EmployeeRole] = mapped_column(
        Enum(EmployeeRole, name="employeerole"), nullable=False, default=EmployeeRole.EMPLOYEE
    )
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.employee_id"), nullable=True)
    skills: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    skills_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    availability_status: Mapped[EmployeeAvailabilityStatus | None] = mapped_column(
        Enum(EmployeeAvailabilityStatus, name="employeeavailabilitystatus"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    manager: Mapped["Employee | None"] = relationship(remote_side=[employee_id], foreign_keys=[manager_id])


class Availability(Base, AuditMixin):
    __tablename__ = "availability"
    __table_args__ = (
        CheckConstraint(
            "allocation_percent IS NULL OR (allocation_percent >= 0 AND allocation_percent <= 100)",
            name="ck_availability_allocation_percent_range",
        ),
    )

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), primary_key=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    skill_set: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allocation_percent: Mapped[float | None] = mapped_column(Float, nullable=True)


class SelfReport(Base, AuditMixin):
    """One free-text profile/self-report submission per employee per cycle.

    `profile_text` is employee-authored free text: per CLAUDE.md §6/§7,
    never log it (log the `self_report_id` instead), and treat it as
    untrusted input wherever it's later fed into a scoring prompt — strip
    instruction-like content before inclusion, same as any other
    self-report text.
    """

    __tablename__ = "self_reports"
    __table_args__ = (UniqueConstraint("employee_id", "cycle_id", name="uq_self_reports_employee_cycle"),)

    self_report_id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.cycle_id"), nullable=False)
    profile_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

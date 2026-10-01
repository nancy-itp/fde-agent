from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.mixins import AuditMixin


class MismatchFlag(Base, AuditMixin):
    """A detected self-report-vs-tracker mismatch for one employee/cycle/dimension.

    Per CLAUDE.md §7, every mismatch *resolution* also belongs in the
    append-only audit log (actor, timestamp, before/after) — this row is the
    current-state record the review queue works from, not the audit trail
    itself.
    """

    __tablename__ = "mismatch_flags"

    mismatch_flag_id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.cycle_id"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(255), nullable=False)
    self_report_claim: Mapped[str] = mapped_column(Text, nullable=False)
    tracker_fact: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("employees.employee_id"), nullable=True)

import enum
from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.mixins import AuditMixin


class ReviewCycleStatus(enum.StrEnum):
    DRAFT = "Draft"
    OPEN = "Open"
    CLOSED = "Closed"


class ReviewCycle(Base, AuditMixin):
    __tablename__ = "review_cycles"
    __table_args__ = (CheckConstraint("cycle_end > cycle_start", name="ck_review_cycles_end_after_start"),)

    cycle_id: Mapped[int] = mapped_column(primary_key=True)
    cycle_start: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ReviewCycleStatus] = mapped_column(
        Enum(ReviewCycleStatus, name="reviewcyclestatus"), nullable=False, default=ReviewCycleStatus.DRAFT
    )

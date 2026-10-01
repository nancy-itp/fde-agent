from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.mixins import AuditMixin
from app.prio_integration.schemas import JSONValue


class PrioSnapshot(Base, AuditMixin):
    __tablename__ = "prio_snapshots"

    snapshot_id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.cycle_id"), nullable=False)
    ticket_data_json: Mapped[dict[str, JSONValue]] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.mixins import AuditMixin


class PerformanceScore(Base, AuditMixin):
    __tablename__ = "performance_scores"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_performance_scores_score_range"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_performance_scores_confidence_range",
        ),
    )

    score_id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.cycle_id"), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class ApiCallType(enum.StrEnum):
    CROSS_CHECK = "cross_check"
    DOC_GRADING = "doc_grading"
    COACHING_TEXT = "coaching_text"
    TECHNICAL_FUNDAMENTALS = "technical_fundamentals"
    MANUAL_RERUN = "manual_rerun"


class ApiCallStatus(enum.StrEnum):
    SUCCESS = "success"
    RETRIED = "retried"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


class ApiCallLog(Base):
    """Append-only log, one row per Claude API call (see

    `docs/COST_LOGGING_AND_OPTIMIZATION.md` §Schema). No `AuditMixin` here —
    this is a system-generated event log, not a user-editable entity, and
    every field is fixed at insert time with one documented exception:
    `manager_overrode` is filled in later, once a manager's review decision
    on the dimension this call scored is known.
    """

    __tablename__ = "api_call_logs"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("review_cycles.cycle_id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.employee_id"), nullable=False)
    dimension: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_type: Mapped[ApiCallType] = mapped_column(Enum(ApiCallType, name="apicalltype"), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    batched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ApiCallStatus] = mapped_column(Enum(ApiCallStatus, name="apicallstatus"), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    routed_to_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manager_overrode: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

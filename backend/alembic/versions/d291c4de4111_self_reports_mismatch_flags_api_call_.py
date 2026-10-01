"""self reports, mismatch flags, api call logs

Revision ID: d291c4de4111
Revises: a2f53062f9a9
Create Date: 2026-09-30 21:54:09.955736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd291c4de4111'
down_revision: Union[str, None] = 'a2f53062f9a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

api_call_type = sa.Enum(
    "CROSS_CHECK", "DOC_GRADING", "COACHING_TEXT", "TECHNICAL_FUNDAMENTALS", "MANUAL_RERUN", name="apicalltype"
)
api_call_status = sa.Enum("SUCCESS", "RETRIED", "FAILED", "VALIDATION_FAILED", name="apicallstatus")


def _audit_columns() -> list[sa.Column]:
    """Standard created_at/created_by/updated_at/updated_by columns for every table."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "self_reports",
        sa.Column("self_report_id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("review_cycles.cycle_id"), nullable=False),
        sa.Column("profile_text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_audit_columns(),
        sa.UniqueConstraint("employee_id", "cycle_id", name="uq_self_reports_employee_cycle"),
    )

    op.create_table(
        "mismatch_flags",
        sa.Column("mismatch_flag_id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("review_cycles.cycle_id"), nullable=False),
        sa.Column("dimension", sa.String(255), nullable=False),
        sa.Column("self_report_claim", sa.Text(), nullable=False),
        sa.Column("tracker_fact", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=True),
        *_audit_columns(),
    )

    op.create_table(
        "api_call_logs",
        sa.Column("call_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("review_cycles.cycle_id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("dimension", sa.String(255), nullable=True),
        sa.Column("call_type", api_call_type, nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("batched", sa.Boolean(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_creation_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", api_call_status, nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("routed_to_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("manager_overrode", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("api_call_logs")
    op.drop_table("mismatch_flags")
    op.drop_table("self_reports")

    api_call_status.drop(op.get_bind(), checkfirst=True)
    api_call_type.drop(op.get_bind(), checkfirst=True)

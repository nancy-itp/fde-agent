"""initial schema

Revision ID: a2f53062f9a9
Revises:
Create Date: 2026-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2f53062f9a9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

employee_role = sa.Enum("EMPLOYEE", "MANAGER", "ADMIN", name="employeerole")
employee_availability_status = sa.Enum(
    "AVAILABLE", "UNAVAILABLE", "PARTIALLY_AVAILABLE", name="employeeavailabilitystatus"
)
review_cycle_status = sa.Enum("DRAFT", "OPEN", "CLOSED", name="reviewcyclestatus")


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
        "employees",
        sa.Column("employee_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", employee_role, nullable=False),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("skills", sa.String(1000), nullable=True),
        sa.Column("skills_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability_status", employee_availability_status, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_audit_columns(),
    )

    op.create_table(
        "review_cycles",
        sa.Column("cycle_id", sa.Integer(), primary_key=True),
        sa.Column("cycle_start", sa.Date(), nullable=False),
        sa.Column("cycle_end", sa.Date(), nullable=False),
        sa.Column("status", review_cycle_status, nullable=False),
        *_audit_columns(),
        sa.CheckConstraint("cycle_end > cycle_start", name="ck_review_cycles_end_after_start"),
    )

    op.create_table(
        "prio_snapshots",
        sa.Column("snapshot_id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("review_cycles.cycle_id"), nullable=False),
        sa.Column("ticket_data_json", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_audit_columns(),
    )

    op.create_table(
        "performance_scores",
        sa.Column("score_id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("review_cycles.cycle_id"), nullable=False),
        sa.Column("dimension_name", sa.String(255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_performance_scores_score_range"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_performance_scores_confidence_range",
        ),
    )

    op.create_table(
        "availability",
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.employee_id"), primary_key=True),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("skill_set", sa.String(1000), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("allocation_percent", sa.Float(), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint(
            "allocation_percent IS NULL OR (allocation_percent >= 0 AND allocation_percent <= 100)",
            name="ck_availability_allocation_percent_range",
        ),
    )


def downgrade() -> None:
    op.drop_table("availability")
    op.drop_table("performance_scores")
    op.drop_table("prio_snapshots")
    op.drop_table("review_cycles")
    op.drop_table("employees")

    review_cycle_status.drop(op.get_bind(), checkfirst=True)
    employee_availability_status.drop(op.get_bind(), checkfirst=True)
    employee_role.drop(op.get_bind(), checkfirst=True)

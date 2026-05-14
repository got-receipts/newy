"""initial schema

Revision ID: 202605140001
Revises:
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605140001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("gross_earnings", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("tips", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("trips", sa.Integer(), server_default="0", nullable=False),
        sa.Column("miles", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("gas_cost", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("other_expenses", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("active_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_shifts_user_id"), "shifts", ["user_id"], unique=False)

    op.create_table(
        "breaks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_type", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_breaks_shift_id"), "breaks", ["shift_id"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "platform_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("gross_earnings", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("tips", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("trips", sa.Integer(), server_default="0", nullable=False),
        sa.Column("miles", sa.Numeric(10, 2), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_entries")
    op.drop_table("expenses")
    op.drop_index(op.f("ix_breaks_shift_id"), table_name="breaks")
    op.drop_table("breaks")
    op.drop_index(op.f("ix_shifts_user_id"), table_name="shifts")
    op.drop_table("shifts")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")


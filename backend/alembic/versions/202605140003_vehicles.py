"""vehicles

Revision ID: 202605140003
Revises: 202605140002
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605140003"
down_revision: Union[str, None] = "202605140002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("mpg_city", sa.Numeric(5, 1), nullable=False),
        sa.Column("mpg_highway", sa.Numeric(5, 1), nullable=False),
        sa.Column("mpg_combined", sa.Numeric(5, 1), nullable=False),
        sa.Column("fuel_type", sa.String(length=40), nullable=False, server_default="gasoline"),
    )
    op.create_table(
        "user_vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("vehicle_catalog.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nickname", sa.String(length=80), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("mpg_city", sa.Numeric(5, 1), nullable=False),
        sa.Column("mpg_highway", sa.Numeric(5, 1), nullable=False),
        sa.Column("mpg_combined", sa.Numeric(5, 1), nullable=False),
        sa.Column("fuel_type", sa.String(length=40), nullable=False, server_default="gasoline"),
        sa.Column("fuel_price_per_gallon", sa.Numeric(6, 2), nullable=False, server_default="3.50"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_user_vehicles_user_id"), "user_vehicles", ["user_id"], unique=False)
    op.add_column("shifts", sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("user_vehicles.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("shifts", "vehicle_id")
    op.drop_index(op.f("ix_user_vehicles_user_id"), table_name="user_vehicles")
    op.drop_table("user_vehicles")
    op.drop_table("vehicle_catalog")

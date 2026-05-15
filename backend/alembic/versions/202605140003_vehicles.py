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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "vehicle_catalog" not in tables:
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

    if "user_vehicles" not in tables:
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

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    indexes = {index["name"] for index in inspector.get_indexes("user_vehicles")} if "user_vehicles" in tables else set()
    if op.f("ix_user_vehicles_user_id") not in indexes:
        op.create_index(op.f("ix_user_vehicles_user_id"), "user_vehicles", ["user_id"], unique=False)

    shift_columns = {column["name"] for column in inspector.get_columns("shifts")}
    if "vehicle_id" not in shift_columns:
        op.add_column("shifts", sa.Column("vehicle_id", sa.Integer(), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_shifts_vehicle_id_user_vehicles",
                "shifts",
                "user_vehicles",
                ["vehicle_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "shifts" in tables and "vehicle_id" in {column["name"] for column in inspector.get_columns("shifts")}:
        op.drop_column("shifts", "vehicle_id")
    if "user_vehicles" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("user_vehicles")}
        if op.f("ix_user_vehicles_user_id") in indexes:
            op.drop_index(op.f("ix_user_vehicles_user_id"), table_name="user_vehicles")
        op.drop_table("user_vehicles")
    if "vehicle_catalog" in tables:
        op.drop_table("vehicle_catalog")

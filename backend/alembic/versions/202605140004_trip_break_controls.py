"""trip break controls

Revision ID: 202605140004
Revises: 202605140003
Create Date: 2026-05-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605140004"
down_revision: Union[str, None] = "202605140003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("shifts")}
    if "trips_since_break" not in columns:
        op.add_column("shifts", sa.Column("trips_since_break", sa.Integer(), nullable=False, server_default="0"))
    if "last_trip_at" not in columns:
        op.add_column("shifts", sa.Column("last_trip_at", sa.DateTime(timezone=True), nullable=True))
    if "break_required" not in columns:
        op.add_column("shifts", sa.Column("break_required", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("shifts")}
    if "break_required" in columns:
        op.drop_column("shifts", "break_required")
    if "last_trip_at" in columns:
        op.drop_column("shifts", "last_trip_at")
    if "trips_since_break" in columns:
        op.drop_column("shifts", "trips_since_break")

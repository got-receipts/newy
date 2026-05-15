"""manual break overrides

Revision ID: 202605150005
Revises: 202605140004
Create Date: 2026-05-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605150005"
down_revision: Union[str, None] = "202605140004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    shift_columns = {column["name"] for column in inspector.get_columns("shifts")}
    break_columns = {column["name"] for column in inspector.get_columns("breaks")}

    if "manual_break_followup_due_at" not in shift_columns:
        op.add_column("shifts", sa.Column("manual_break_followup_due_at", sa.DateTime(timezone=True), nullable=True))
    if "manual_break_followup_trips" not in shift_columns:
        op.add_column("shifts", sa.Column("manual_break_followup_trips", sa.Integer(), nullable=False, server_default="0"))

    if "manual_override" not in break_columns:
        op.add_column("breaks", sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "planned_minutes" not in break_columns:
        op.add_column("breaks", sa.Column("planned_minutes", sa.Numeric(4, 1), nullable=False, server_default="15.0"))
    if "target_distance_feet" not in break_columns:
        op.add_column("breaks", sa.Column("target_distance_feet", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    shift_columns = {column["name"] for column in inspector.get_columns("shifts")}
    break_columns = {column["name"] for column in inspector.get_columns("breaks")}

    if "target_distance_feet" in break_columns:
        op.drop_column("breaks", "target_distance_feet")
    if "planned_minutes" in break_columns:
        op.drop_column("breaks", "planned_minutes")
    if "manual_override" in break_columns:
        op.drop_column("breaks", "manual_override")
    if "manual_break_followup_trips" in shift_columns:
        op.drop_column("shifts", "manual_break_followup_trips")
    if "manual_break_followup_due_at" in shift_columns:
        op.drop_column("shifts", "manual_break_followup_due_at")

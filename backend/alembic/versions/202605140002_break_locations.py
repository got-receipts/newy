"""break locations

Revision ID: 202605140002
Revises: 202605140001
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605140002"
down_revision: Union[str, None] = "202605140001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("breaks", sa.Column("location_name", sa.String(length=255), nullable=True))
    op.add_column("breaks", sa.Column("latitude", sa.Numeric(9, 6), nullable=True))
    op.add_column("breaks", sa.Column("longitude", sa.Numeric(9, 6), nullable=True))
    op.add_column("breaks", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("breaks", "confirmed_at")
    op.drop_column("breaks", "longitude")
    op.drop_column("breaks", "latitude")
    op.drop_column("breaks", "location_name")


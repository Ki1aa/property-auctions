"""add lot municipality fields

Revision ID: 20260507_07
Revises: 20260506_06
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260507_07"
down_revision = "20260506_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("permitted_use_codes", sa.String(length=256), nullable=True))
    op.add_column("lots", sa.Column("municipality", sa.String(length=256), nullable=True))
    op.add_column("lots", sa.Column("settlement", sa.String(length=256), nullable=True))
    op.create_index("ix_lots_municipality", "lots", ["municipality"], unique=False)
    op.create_index("ix_lots_settlement", "lots", ["settlement"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lots_settlement", table_name="lots")
    op.drop_index("ix_lots_municipality", table_name="lots")
    op.drop_column("lots", "settlement")
    op.drop_column("lots", "municipality")
    op.drop_column("lots", "permitted_use_codes")

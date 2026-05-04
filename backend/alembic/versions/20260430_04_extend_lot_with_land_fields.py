"""extend lots with land plot fields

Revision ID: 20260430_04
Revises: 20260428_03
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_04"
down_revision = "20260428_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("cadastral_number", sa.String(length=64), nullable=True))
    op.add_column("lots", sa.Column("area_sqm", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("land_category", sa.String(length=256), nullable=True))
    op.add_column("lots", sa.Column("permitted_use", sa.Text(), nullable=True))
    op.add_column("lots", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("lots", sa.Column("notice_detail_url", sa.Text(), nullable=True))
    op.add_column(
        "lots",
        sa.Column("is_izhs_candidate", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_lots_cadastral_number", "lots", ["cadastral_number"], unique=False)
    op.create_index("ix_lots_is_izhs_candidate", "lots", ["is_izhs_candidate"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lots_is_izhs_candidate", table_name="lots")
    op.drop_index("ix_lots_cadastral_number", table_name="lots")
    op.drop_column("lots", "is_izhs_candidate")
    op.drop_column("lots", "notice_detail_url")
    op.drop_column("lots", "address")
    op.drop_column("lots", "permitted_use")
    op.drop_column("lots", "land_category")
    op.drop_column("lots", "area_sqm")
    op.drop_column("lots", "cadastral_number")

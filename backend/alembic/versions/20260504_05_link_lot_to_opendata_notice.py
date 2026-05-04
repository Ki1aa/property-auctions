"""link lot to opendata notice

Revision ID: 20260504_05
Revises: 20260430_04
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_05"
down_revision = "20260430_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("opendata_notice_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_lots_opendata_notice_id",
        "lots",
        ["opendata_notice_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_lots_opendata_notice_id_opendata_notices",
        source_table="lots",
        referent_table="opendata_notices",
        local_cols=["opendata_notice_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_lots_opendata_notice_id_opendata_notices", "lots", type_="foreignkey"
    )
    op.drop_index("ix_lots_opendata_notice_id", table_name="lots")
    op.drop_column("lots", "opendata_notice_id")

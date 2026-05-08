"""add opendata notice sort indexes

Revision ID: 20260508_08
Revises: 20260507_07
Create Date: 2026-05-08
"""

from alembic import op


revision = "20260508_08"
down_revision = "20260507_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_opendata_notices_reg_num_id", "opendata_notices", ["reg_num", "id"], unique=False)
    op.create_index(
        "ix_opendata_notices_document_type_id",
        "opendata_notices",
        ["document_type", "id"],
        unique=False,
    )
    op.create_index(
        "ix_opendata_notices_bidd_type_code_id",
        "opendata_notices",
        ["bidd_type_code", "id"],
        unique=False,
    )
    op.create_index(
        "ix_opendata_notices_publish_date_id",
        "opendata_notices",
        ["publish_date", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_opendata_notices_publish_date_id", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_bidd_type_code_id", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_document_type_id", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_reg_num_id", table_name="opendata_notices")

"""add opendata notices table

Revision ID: 20260428_02
Revises: 20260423_01
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_02"
down_revision = "20260423_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opendata_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reg_num", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=True),
        sa.Column("publish_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("href", sa.Text(), nullable=False),
        sa.Column("bidder_org_code", sa.String(length=32), nullable=True),
        sa.Column("right_holder_code", sa.String(length=32), nullable=True),
        sa.Column("bidd_type_code", sa.String(length=64), nullable=True),
        sa.Column("ownership_forms_code", sa.String(length=32), nullable=True),
        sa.Column("subject_estate_code", sa.String(length=32), nullable=True),
        sa.Column("subject_right_holder_code", sa.String(length=32), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("structure_version", sa.String(length=32), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_opendata_notices_reg_num", "opendata_notices", ["reg_num"], unique=False)
    op.create_index("ix_opendata_notices_document_type", "opendata_notices", ["document_type"], unique=False)
    op.create_index("ix_opendata_notices_publish_date", "opendata_notices", ["publish_date"], unique=False)
    op.create_index("ix_opendata_notices_href", "opendata_notices", ["href"], unique=True)
    op.create_index("ix_opendata_notices_bidd_type_code", "opendata_notices", ["bidd_type_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_opendata_notices_bidd_type_code", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_href", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_publish_date", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_document_type", table_name="opendata_notices")
    op.drop_index("ix_opendata_notices_reg_num", table_name="opendata_notices")
    op.drop_table("opendata_notices")

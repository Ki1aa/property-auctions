"""add ingest manifest table

Revision ID: 20260428_03
Revises: 20260428_02
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_03"
down_revision = "20260428_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_manifest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("structure_url", sa.Text(), nullable=True),
        sa.Column("data_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_url", "sha256", name="uq_ingest_manifest_source_sha256"),
    )
    op.create_index("ix_ingest_manifest_provider", "ingest_manifest", ["provider"], unique=False)
    op.create_index("ix_ingest_manifest_dataset_id", "ingest_manifest", ["dataset_id"], unique=False)
    op.create_index("ix_ingest_manifest_data_from", "ingest_manifest", ["data_from"], unique=False)
    op.create_index("ix_ingest_manifest_data_to", "ingest_manifest", ["data_to"], unique=False)
    op.create_index("ix_ingest_manifest_schema_version", "ingest_manifest", ["schema_version"], unique=False)
    op.create_index("ix_ingest_manifest_sha256", "ingest_manifest", ["sha256"], unique=False)
    op.create_index("ix_ingest_manifest_status", "ingest_manifest", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ingest_manifest_status", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_sha256", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_schema_version", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_data_to", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_data_from", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_dataset_id", table_name="ingest_manifest")
    op.drop_index("ix_ingest_manifest_provider", table_name="ingest_manifest")
    op.drop_table("ingest_manifest")

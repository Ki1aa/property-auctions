"""add ingest observability fields

Revision ID: 20260506_06
Revises: 20260504_05
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_06"
down_revision = "20260504_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingest_runs",
        sa.Column("processed_files", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingest_runs",
        sa.Column("failed_files", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("ingest_runs", sa.Column("last_error_source_url", sa.Text(), nullable=True))
    op.add_column("ingest_runs", sa.Column("error_kind", sa.String(length=64), nullable=True))
    op.create_index("ix_ingest_runs_error_kind", "ingest_runs", ["error_kind"], unique=False)

    op.add_column("ingest_manifest", sa.Column("error_kind", sa.String(length=64), nullable=True))
    op.create_index("ix_ingest_manifest_error_kind", "ingest_manifest", ["error_kind"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ingest_manifest_error_kind", table_name="ingest_manifest")
    op.drop_column("ingest_manifest", "error_kind")

    op.drop_index("ix_ingest_runs_error_kind", table_name="ingest_runs")
    op.drop_column("ingest_runs", "error_kind")
    op.drop_column("ingest_runs", "last_error_source_url")
    op.drop_column("ingest_runs", "failed_files")
    op.drop_column("ingest_runs", "processed_files")

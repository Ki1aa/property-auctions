"""Add NSPD enrichment columns to lots."""

from alembic import op
import sqlalchemy as sa


revision = "20260509_09_add_lot_nspd_fields"
down_revision = "20260508_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("nspd_specified_area_sqm", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("nspd_readable_address", sa.Text(), nullable=True))
    op.add_column("lots", sa.Column("nspd_cost_value", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("nspd_centroid_latitude", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("nspd_centroid_longitude", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("nspd_enriched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("lots", "nspd_enriched_at")
    op.drop_column("lots", "nspd_centroid_longitude")
    op.drop_column("lots", "nspd_centroid_latitude")
    op.drop_column("lots", "nspd_cost_value")
    op.drop_column("lots", "nspd_readable_address")
    op.drop_column("lots", "nspd_specified_area_sqm")

"""Add market_comparables table for future Cian/aggregator snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "20260509_10_market_comparables"
down_revision = "20260509_09_add_lot_nspd_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_comparables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_listing_id", sa.String(length=128), nullable=True),
        sa.Column("listing_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("price_rub", sa.Float(), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("region_code", sa.String(length=32), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_market_comparables_lot_id"), "market_comparables", ["lot_id"], unique=False)
    op.create_index(op.f("ix_market_comparables_source"), "market_comparables", ["source"], unique=False)
    op.create_index(
        op.f("ix_market_comparables_external_listing_id"),
        "market_comparables",
        ["external_listing_id"],
        unique=False,
    )
    op.create_index(op.f("ix_market_comparables_region_code"), "market_comparables", ["region_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_market_comparables_region_code"), table_name="market_comparables")
    op.drop_index(op.f("ix_market_comparables_external_listing_id"), table_name="market_comparables")
    op.drop_index(op.f("ix_market_comparables_source"), table_name="market_comparables")
    op.drop_index(op.f("ix_market_comparables_lot_id"), table_name="market_comparables")
    op.drop_table("market_comparables")

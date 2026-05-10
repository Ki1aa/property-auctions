"""Parallel MVP GIS tables (mvp_gis_*); legacy lots unchanged."""

from alembic import op
import sqlalchemy as sa


revision = "20260512_16_mvp_gis_tables"
down_revision = "20260511_14_lot_attrs_map_anchor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mvp_gis_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notice_number", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=128), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_mvp_gis_notices_notice_number", "mvp_gis_notices", ["notice_number"], unique=True)

    op.create_table(
        "mvp_gis_lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notice_id", sa.Integer(), sa.ForeignKey("mvp_gis_notices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notice_number", sa.String(length=64), nullable=False),
        sa.Column("lot_number", sa.String(length=32), nullable=False),
        sa.Column("lot_external_id", sa.String(length=256), nullable=False),
        sa.Column("region_code", sa.String(length=32), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cadastral_number", sa.String(length=64), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("start_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=128), nullable=True),
        sa.Column("application_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permitted_use", sa.Text(), nullable=True),
        sa.Column("land_category", sa.String(length=512), nullable=True),
        sa.Column("price_per_sqm", sa.Float(), nullable=True),
        sa.Column("price_per_100sqm", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("coordinates_source", sa.String(length=64), nullable=True),
        sa.Column("coordinates_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notice_url", sa.Text(), nullable=True),
        sa.Column("lot_url", sa.Text(), nullable=True),
        sa.Column("nspd_url", sa.Text(), nullable=True),
        sa.Column("domclick_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("is_land", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_housing_candidate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("signal_level", sa.String(length=16), nullable=False, server_default="NONE"),
        sa.Column("is_ignored", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ignored_reason", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_mvp_gis_lots_notice_id", "mvp_gis_lots", ["notice_id"])
    op.create_index("ix_mvp_gis_lots_region", "mvp_gis_lots", ["region_code"])
    op.create_index("ix_mvp_gis_lots_signal", "mvp_gis_lots", ["signal_level"])
    op.create_index("ix_mvp_gis_lots_cadastral", "mvp_gis_lots", ["cadastral_number"])
    op.create_index("ix_mvp_gis_lots_content_hash", "mvp_gis_lots", ["content_hash"])
    op.create_index("uq_mvp_gis_lot_external_id", "mvp_gis_lots", ["lot_external_id"], unique=True)
    op.create_index("uq_mvp_gis_notice_lot_number", "mvp_gis_lots", ["notice_number", "lot_number"], unique=True)

    op.create_table(
        "mvp_gis_lot_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("mvp_gis_lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("changed_fields_json", sa.JSON(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_mvp_gis_lot_versions_lot_id", "mvp_gis_lot_versions", ["lot_id"])
    op.create_index("ix_mvp_gis_lot_versions_hash", "mvp_gis_lot_versions", ["content_hash"])

    op.create_table(
        "mvp_gis_telegram_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("mvp_gis_lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mvp_gis_telegram_lot", "mvp_gis_telegram_events", ["lot_id"])
    op.create_index("ix_mvp_gis_telegram_status", "mvp_gis_telegram_events", ["status"])
    op.create_index(
        "uq_mvp_gis_telegram_event",
        "mvp_gis_telegram_events",
        ["lot_id", "event_type", "content_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_mvp_gis_telegram_event", table_name="mvp_gis_telegram_events")
    op.drop_index("ix_mvp_gis_telegram_status", table_name="mvp_gis_telegram_events")
    op.drop_index("ix_mvp_gis_telegram_lot", table_name="mvp_gis_telegram_events")
    op.drop_table("mvp_gis_telegram_events")

    op.drop_index("ix_mvp_gis_lot_versions_hash", table_name="mvp_gis_lot_versions")
    op.drop_index("ix_mvp_gis_lot_versions_lot_id", table_name="mvp_gis_lot_versions")
    op.drop_table("mvp_gis_lot_versions")

    op.drop_index("uq_mvp_gis_notice_lot_number", table_name="mvp_gis_lots")
    op.drop_index("uq_mvp_gis_lot_external_id", table_name="mvp_gis_lots")
    op.drop_index("ix_mvp_gis_lots_content_hash", table_name="mvp_gis_lots")
    op.drop_index("ix_mvp_gis_lots_cadastral", table_name="mvp_gis_lots")
    op.drop_index("ix_mvp_gis_lots_signal", table_name="mvp_gis_lots")
    op.drop_index("ix_mvp_gis_lots_region", table_name="mvp_gis_lots")
    op.drop_index("ix_mvp_gis_lots_notice_id", table_name="mvp_gis_lots")
    op.drop_table("mvp_gis_lots")

    op.drop_index("ix_mvp_gis_notices_notice_number", table_name="mvp_gis_notices")
    op.drop_table("mvp_gis_notices")

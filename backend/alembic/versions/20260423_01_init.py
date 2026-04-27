"""init schema

Revision ID: 20260423_01
Revises:
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("inn", sa.String(length=20), nullable=True),
        sa.Column("kpp", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_organizers_source_id", "organizers", ["source_id"], unique=True)

    op.create_table(
        "lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=256), nullable=True),
        sa.Column("category", sa.String(length=256), nullable=True),
        sa.Column("start_price", sa.Float(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("organizers.id"), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_lots_source_id", "lots", ["source_id"], unique=True)
    op.create_index("ix_lots_status", "lots", ["status"], unique=False)
    op.create_index("ix_lots_region", "lots", ["region"], unique=False)
    op.create_index("ix_lots_category", "lots", ["category"], unique=False)
    op.create_index("ix_lots_start_date", "lots", ["start_date"], unique=False)
    op.create_index("ix_lots_end_date", "lots", ["end_date"], unique=False)

    op.create_table(
        "lot_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("lot_id", "payload_hash", name="uq_lot_snapshot_hash"),
    )
    op.create_index("ix_lot_snapshots_lot_id", "lot_snapshots", ["lot_id"], unique=False)
    op.create_index("ix_lot_snapshots_payload_hash", "lot_snapshots", ["payload_hash"], unique=False)

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_ingest_runs_status", "ingest_runs", ["status"], unique=False)

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("lot_id", "event_type", "event_hash", name="uq_alert_event"),
    )
    op.create_index("ix_alert_events_lot_id", "alert_events", ["lot_id"], unique=False)
    op.create_index("ix_alert_events_event_type", "alert_events", ["event_type"], unique=False)
    op.create_index("ix_alert_events_event_hash", "alert_events", ["event_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_events_event_hash", table_name="alert_events")
    op.drop_index("ix_alert_events_event_type", table_name="alert_events")
    op.drop_index("ix_alert_events_lot_id", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_ingest_runs_status", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_index("ix_lot_snapshots_payload_hash", table_name="lot_snapshots")
    op.drop_index("ix_lot_snapshots_lot_id", table_name="lot_snapshots")
    op.drop_table("lot_snapshots")
    op.drop_index("ix_lots_end_date", table_name="lots")
    op.drop_index("ix_lots_start_date", table_name="lots")
    op.drop_index("ix_lots_category", table_name="lots")
    op.drop_index("ix_lots_region", table_name="lots")
    op.drop_index("ix_lots_status", table_name="lots")
    op.drop_index("ix_lots_source_id", table_name="lots")
    op.drop_table("lots")
    op.drop_index("ix_organizers_source_id", table_name="organizers")
    op.drop_table("organizers")

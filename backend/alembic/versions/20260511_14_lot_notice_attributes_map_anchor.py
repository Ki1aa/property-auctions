"""Lot notice characteristics (EAV) and canonical map anchor on lots."""

from alembic import op
import sqlalchemy as sa


revision = "20260511_14_lot_attrs_map_anchor"
down_revision = "20260511_13_digest_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lot_notice_attributes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="notice_detail"),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_lot_notice_attributes_lot_id", "lot_notice_attributes", ["lot_id"])
    op.create_index("ix_lot_notice_attributes_code", "lot_notice_attributes", ["code"])
    op.create_index(
        "ix_lot_notice_attributes_lot_code",
        "lot_notice_attributes",
        ["lot_id", "code"],
    )
    op.create_index(
        "ix_lot_notice_attributes_code_value_text",
        "lot_notice_attributes",
        ["code", "value_text"],
    )

    op.add_column("lots", sa.Column("map_anchor_latitude", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("map_anchor_longitude", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("map_anchor_source", sa.String(length=32), nullable=True))
    op.add_column("lots", sa.Column("map_anchor_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("lots", "map_anchor_updated_at")
    op.drop_column("lots", "map_anchor_source")
    op.drop_column("lots", "map_anchor_longitude")
    op.drop_column("lots", "map_anchor_latitude")

    op.drop_index("ix_lot_notice_attributes_code_value_text", table_name="lot_notice_attributes")
    op.drop_index("ix_lot_notice_attributes_lot_code", table_name="lot_notice_attributes")
    op.drop_index("ix_lot_notice_attributes_code", table_name="lot_notice_attributes")
    op.drop_index("ix_lot_notice_attributes_lot_id", table_name="lot_notice_attributes")
    op.drop_table("lot_notice_attributes")

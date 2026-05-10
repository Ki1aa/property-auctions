"""Telegram digest queue table."""

from alembic import op
import sqlalchemy as sa


revision = "20260511_13_digest_items"
down_revision = "20260510_12_notice_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_digest_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_telegram_digest_items_lot_id", "telegram_digest_items", ["lot_id"])
    op.create_index("ix_telegram_digest_items_event_type", "telegram_digest_items", ["event_type"])
    op.create_index("ix_telegram_digest_items_event_hash", "telegram_digest_items", ["event_hash"])


def downgrade() -> None:
    op.drop_index("ix_telegram_digest_items_event_hash", table_name="telegram_digest_items")
    op.drop_index("ix_telegram_digest_items_event_type", table_name="telegram_digest_items")
    op.drop_index("ix_telegram_digest_items_lot_id", table_name="telegram_digest_items")
    op.drop_table("telegram_digest_items")

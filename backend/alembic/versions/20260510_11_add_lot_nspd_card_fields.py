"""Add NSPD public map card identifiers to lots."""

from alembic import op
import sqlalchemy as sa


revision = "20260510_11_lot_nspd_card_fields"
down_revision = "20260509_10_market_comparables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("nspd_card_id", sa.String(length=64), nullable=True))
    op.add_column("lots", sa.Column("nspd_card_type", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("lots", "nspd_card_type")
    op.drop_column("lots", "nspd_card_id")

"""Add stable GIS Torgi notice identity fields to lots."""

from alembic import op
import sqlalchemy as sa


revision = "20260510_12_lot_notice_identity_fields"
down_revision = "20260510_11_lot_nspd_card_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("notice_reg_num", sa.String(length=64), nullable=True))
    op.add_column("lots", sa.Column("notice_lot_number", sa.String(length=32), nullable=True))
    op.add_column("lots", sa.Column("notice_lot_count", sa.Integer(), nullable=True))
    op.create_index("ix_lots_notice_reg_num", "lots", ["notice_reg_num"])
    op.create_index("ix_lots_notice_lot_number", "lots", ["notice_lot_number"])


def downgrade() -> None:
    op.drop_index("ix_lots_notice_lot_number", table_name="lots")
    op.drop_index("ix_lots_notice_reg_num", table_name="lots")
    op.drop_column("lots", "notice_lot_count")
    op.drop_column("lots", "notice_lot_number")
    op.drop_column("lots", "notice_reg_num")

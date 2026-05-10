"""Lot: NSPD map Web Mercator center (coordinate_x / coordinate_y) for deep links and Domclick."""

from alembic import op
import sqlalchemy as sa


revision = "20260512_15_nspd_map_mercator"
down_revision = "20260511_14_lot_attrs_map_anchor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lots", sa.Column("nspd_map_coordinate_x", sa.Float(), nullable=True))
    op.add_column("lots", sa.Column("nspd_map_coordinate_y", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("lots", "nspd_map_coordinate_y")
    op.drop_column("lots", "nspd_map_coordinate_x")

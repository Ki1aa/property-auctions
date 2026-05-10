"""Fill lots.nspd_map_coordinate_x/y from nspd_centroid_* (WGS84) when Mercator is missing."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Lot
from app.services.nspd.geometry import wgs84_to_epsg3857


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(Lot.id).where(
                Lot.nspd_centroid_latitude.is_not(None),
                Lot.nspd_centroid_longitude.is_not(None),
                Lot.nspd_map_coordinate_x.is_(None),
            )
        ).all()
        n = 0
        for lot_id in rows:
            lot = db.get(Lot, lot_id)
            if lot is None:
                continue
            lat, lon = float(lot.nspd_centroid_latitude or 0), float(lot.nspd_centroid_longitude or 0)
            mx, my = wgs84_to_epsg3857(lat, lon)
            lot.nspd_map_coordinate_x = mx
            lot.nspd_map_coordinate_y = my
            n += 1
        db.commit()
        print(f"updated {n} lot(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()

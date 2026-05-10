"""Re-extract GIS Torgi characteristics from latest LotSnapshot and refresh map anchors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Lot, LotNoticeAttribute, LotSnapshot
from app.services.ingest.detail_parser import extract_notice_characteristic_rows
from app.services.map_anchor import refresh_lot_map_anchor


def _replace_attributes(db: Session, lot_id: int, rows: list[dict]) -> None:
    db.execute(delete(LotNoticeAttribute).where(LotNoticeAttribute.lot_id == lot_id))
    for row in rows:
        code = row.get("code")
        if not code or not str(code).strip():
            continue
        value_text = row.get("value_text")
        if isinstance(value_text, str):
            value_text = value_text.strip() or None
        db.add(
            LotNoticeAttribute(
                lot_id=lot_id,
                code=str(code).strip()[:128],
                value_text=value_text,
                value_json=row.get("value_json"),
                source=str(row.get("source") or "notice_detail").strip()[:32] or "notice_detail",
                ordinal=int(row.get("ordinal") or 0),
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Max lots to process (0 = all)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stmt = select(Lot).order_by(Lot.id)
        if args.limit and args.limit > 0:
            stmt = stmt.limit(args.limit)
        lots = db.scalars(stmt).all()
        updated = 0
        for lot in lots:
            snap = db.scalar(
                select(LotSnapshot).where(LotSnapshot.lot_id == lot.id).order_by(LotSnapshot.id.desc())
            )
            payload = snap.payload if snap is not None and isinstance(snap.payload, dict) else {}
            attr_rows = extract_notice_characteristic_rows(payload)
            _replace_attributes(db, lot.id, attr_rows)
            refresh_lot_map_anchor(lot)
            updated += 1
            if updated % 200 == 0:
                db.commit()
        db.commit()
        print(f"backfill complete: {updated} lots")
    finally:
        db.close()


if __name__ == "__main__":
    main()

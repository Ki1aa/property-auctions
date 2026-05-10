"""Backfill stable GIS Torgi notice identity fields on existing Lot rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import desc, select

from app.database import SessionLocal
from app.models import Lot, LotSnapshot, OpenDataNotice
from app.services.lot_identity import lot_notice_identity


def _latest_snapshot_payload(db, lot_id: int) -> dict[str, Any] | None:
    snapshot = db.scalar(
        select(LotSnapshot).where(LotSnapshot.lot_id == lot_id).order_by(desc(LotSnapshot.id))
    )
    if snapshot is not None and isinstance(snapshot.payload, dict):
        return snapshot.payload
    return None


def _notice_payload(db, notice_id: int | None) -> dict[str, Any] | None:
    if notice_id is None:
        return None
    notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.id == notice_id))
    if notice is not None and isinstance(notice.payload, dict):
        return notice.payload
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить notice_reg_num/lot_number/lot_count у существующих Lot.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    counts = {
        "lots_total": 0,
        "with_identity_before": 0,
        "updated": 0,
        "still_missing_reg_num": 0,
        "still_missing_lot_number": 0,
    }

    db = SessionLocal()
    try:
        lots = db.scalars(select(Lot).order_by(Lot.id.asc())).all()
        counts["lots_total"] = len(lots)
        for lot in lots:
            if lot.notice_reg_num and lot.notice_lot_number:
                counts["with_identity_before"] += 1

            identity = lot_notice_identity(
                lot,
                latest_payload=_latest_snapshot_payload(db, lot.id),
                notice_payload=_notice_payload(db, lot.opendata_notice_id),
            )

            if not identity.reg_num:
                counts["still_missing_reg_num"] += 1
            if not identity.lot_number:
                counts["still_missing_lot_number"] += 1

            changed = (
                lot.notice_reg_num != identity.reg_num
                or lot.notice_lot_number != identity.lot_number
                or lot.notice_lot_count != identity.lot_count
            )
            if not changed:
                continue

            counts["updated"] += 1
            if not args.dry_run:
                lot.notice_reg_num = identity.reg_num
                lot.notice_lot_number = identity.lot_number
                lot.notice_lot_count = identity.lot_count

        if not args.dry_run:
            db.commit()
    finally:
        db.close()

    print("Lot notice identity backfill:")
    print(f"- mode: {'dry-run' if args.dry_run else 'apply'}")
    print(f"- lots_total={counts['lots_total']}")
    print(f"- with_identity_before={counts['with_identity_before']}")
    print(f"- updated={counts['updated']}")
    print(f"- still_missing_reg_num={counts['still_missing_reg_num']}")
    print(f"- still_missing_lot_number={counts['still_missing_lot_number']}")


if __name__ == "__main__":
    main()

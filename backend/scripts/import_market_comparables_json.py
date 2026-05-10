"""Import MarketComparable rows from a JSON file (manual analog collection).

Each element must be an object with at least: source, price_rub, area_sqm.
Optional: lot_id, region_code, listing_url, title, external_listing_id, snapshot_json.

Example:
    python scripts/import_market_comparables_json.py --file data/raw/comparables.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import MarketComparable


def main() -> None:
    parser = argparse.ArgumentParser(description="Import market comparables from JSON array file.")
    parser.add_argument("--file", required=True, help="Path to JSON array of comparable objects")
    args = parser.parse_args()
    path = Path(args.file)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("JSON root must be an array")

    db = SessionLocal()
    try:
        inserted = 0
        for item in raw:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or "").strip()
            if not source:
                continue
            price = item.get("price_rub")
            area = item.get("area_sqm")
            if price is None or area is None:
                continue
            lot_id = item.get("lot_id")
            row = MarketComparable(
                lot_id=int(lot_id) if lot_id is not None else None,
                source=source,
                external_listing_id=str(item["external_listing_id"]).strip() if item.get("external_listing_id") else None,
                listing_url=str(item["listing_url"]).strip() if item.get("listing_url") else None,
                title=str(item["title"]).strip() if item.get("title") else None,
                price_rub=float(price),
                area_sqm=float(area),
                region_code=str(item["region_code"]).strip() if item.get("region_code") else None,
                snapshot_json=item.get("snapshot_json") if isinstance(item.get("snapshot_json"), dict) else None,
            )
            db.add(row)
            inserted += 1
        db.commit()
    finally:
        db.close()

    print(f"Imported {inserted} comparables from {path}")


if __name__ == "__main__":
    main()

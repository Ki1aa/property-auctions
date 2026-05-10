"""Backfill Lot.opendata_notice_id by matching existing rows.

Walks every Lot that has opendata_notice_id IS NULL and tries to find a
matching OpenDataNotice via:

1. exact match Lot.source_url == OpenDataNotice.href,
2. fallback: Lot.source_id == OpenDataNotice.reg_num.

Writes a JSON report with totals + a small sample of newly linked pairs.

Usage:
    python scripts/link_lots_to_notices.py
    python scripts/link_lots_to_notices.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Lot, OpenDataNotice
from app.services.lot_identity import lot_notice_identity


DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "link_lots_to_notices_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Слинковать существующие Lot с OpenDataNotice по href/reg_num."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    counts = {
        "lots_total": 0,
        "lots_already_linked": 0,
        "lots_unlinked_before": 0,
        "linked_via_href": 0,
        "linked_via_reg_num": 0,
        "still_unlinked": 0,
        "notices_total": 0,
        "notices_unlinked": 0,
    }

    sample_links: list[dict[str, Any]] = []

    db = SessionLocal()
    try:
        all_lots = db.scalars(select(Lot).order_by(Lot.id.asc())).all()
        counts["lots_total"] = len(all_lots)
        notices_total = db.scalar(select(__import__("sqlalchemy").func.count(OpenDataNotice.id))) or 0
        counts["notices_total"] = int(notices_total)

        href_index: dict[str, int] = {}
        reg_index: dict[str, int] = {}
        notice_payload_index: dict[int, dict[str, Any] | None] = {}
        for notice_id, href, reg_num, payload in db.execute(
            select(OpenDataNotice.id, OpenDataNotice.href, OpenDataNotice.reg_num, OpenDataNotice.payload)
        ):
            if href:
                href_index[href] = notice_id
            if reg_num:
                reg_index.setdefault(reg_num, notice_id)
            notice_payload_index[notice_id] = payload if isinstance(payload, dict) else None

        for lot in all_lots:
            if lot.opendata_notice_id is not None:
                counts["lots_already_linked"] += 1
                continue
            counts["lots_unlinked_before"] += 1

            notice_id: int | None = None
            via: str | None = None
            if lot.source_url and lot.source_url in href_index:
                notice_id = href_index[lot.source_url]
                via = "href"
            elif lot.source_id and lot.source_id in reg_index:
                notice_id = reg_index[lot.source_id]
                via = "reg_num"

            if notice_id is None:
                counts["still_unlinked"] += 1
                continue

            if via == "href":
                counts["linked_via_href"] += 1
            elif via == "reg_num":
                counts["linked_via_reg_num"] += 1

            if len(sample_links) < 25:
                sample_links.append(
                    {
                        "lot_id": lot.id,
                        "lot_source_id": lot.source_id,
                        "lot_source_url_short": (lot.source_url or "")[-80:],
                        "notice_id": notice_id,
                        "matched_via": via,
                    }
                )

            if not args.dry_run:
                lot.opendata_notice_id = notice_id
                identity = lot_notice_identity(lot, notice_payload=notice_payload_index.get(notice_id))
                lot.notice_reg_num = identity.reg_num
                lot.notice_lot_number = identity.lot_number
                lot.notice_lot_count = identity.lot_count

        if not args.dry_run:
            db.commit()

        # Notices that still don't have any lot pointing at them.
        unmatched = db.scalar(
            select(__import__("sqlalchemy").func.count(OpenDataNotice.id)).where(
                ~OpenDataNotice.id.in_(
                    select(Lot.opendata_notice_id).where(Lot.opendata_notice_id.is_not(None))
                )
            )
        ) or 0
        counts["notices_unlinked"] = int(unmatched)
    finally:
        db.close()

    report = {"dry_run": args.dry_run, "counts": counts, "sample_links": sample_links}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Lot <-> OpenDataNotice link report:")
    print(f"- mode: {'dry-run' if args.dry_run else 'apply'}")
    print(f"- lots: total={counts['lots_total']}, already_linked={counts['lots_already_linked']}")
    print(
        f"- linked: via_href={counts['linked_via_href']}, via_reg_num={counts['linked_via_reg_num']}, "
        f"still_unlinked={counts['still_unlinked']}"
    )
    print(f"- notices: total={counts['notices_total']}, without_lot={counts['notices_unlinked']}")
    print(f"- output: {output_path}")


if __name__ == "__main__":
    main()

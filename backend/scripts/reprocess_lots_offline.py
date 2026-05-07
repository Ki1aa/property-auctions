"""Offline reprocessing of existing Lots using saved LotSnapshot.payload.

This script does NOT touch the network. It walks every Lot, finds the most
recent LotSnapshot, and re-applies:

- the latest IZHS keyword set (settings.izhs_keywords) via match_izhs(),
- the cadastral_number / FIAS fields from detail_parser, in case the parser was
  improved since the lot was last ingested.

The opendata index payload typically does NOT contain rich notice-detail
fields (area_sqm / land_category / permitted_use) - those will be enriched
on the next live ingest pass with INGEST_FETCH_NOTICE_DETAILS=true.

Usage:
    python scripts/reprocess_lots_offline.py
    python scripts/reprocess_lots_offline.py --dry-run
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
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Lot, LotSnapshot
from app.services.ingest.detail_parser import (
    match_izhs,
    parse_notice_detail,
    split_keywords,
)


DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "reprocess_lots_offline_report.json"


def _latest_snapshot_payload(db: Session, lot_id: int) -> dict[str, Any] | None:
    snapshot = db.scalar(
        select(LotSnapshot)
        .where(LotSnapshot.lot_id == lot_id)
        .order_by(LotSnapshot.id.desc())
    )
    if snapshot is None:
        return None
    payload = snapshot.payload
    if isinstance(payload, dict):
        return payload
    return None


def reprocess(*, dry_run: bool, limit: int | None) -> dict[str, Any]:
    keywords = split_keywords(settings.izhs_keywords)

    counts = {
        "lots_total": 0,
        "lots_with_snapshot": 0,
        "lots_without_snapshot": 0,
        "izhs_before": 0,
        "izhs_after": 0,
        "izhs_flipped_true": 0,
        "izhs_flipped_false": 0,
        "cadastral_filled_now": 0,
        "cadastral_already_set": 0,
        "cadastral_still_missing": 0,
        "municipality_filled_now": 0,
        "permitted_use_codes_filled_now": 0,
    }

    sample_changes: list[dict[str, Any]] = []

    db = SessionLocal()
    try:
        stmt = select(Lot).order_by(Lot.id.asc())
        if limit:
            stmt = stmt.limit(limit)
        lots = db.scalars(stmt).all()
        counts["lots_total"] = len(lots)

        for lot in lots:
            payload = _latest_snapshot_payload(db, lot.id)
            if payload is None:
                counts["lots_without_snapshot"] += 1
                continue
            counts["lots_with_snapshot"] += 1

            was_izhs = bool(lot.is_izhs_candidate)
            now_izhs = match_izhs(payload, keywords)
            counts["izhs_before"] += int(was_izhs)
            counts["izhs_after"] += int(now_izhs)
            if now_izhs and not was_izhs:
                counts["izhs_flipped_true"] += 1
            if was_izhs and not now_izhs:
                counts["izhs_flipped_false"] += 1

            had_cadastral = lot.cadastral_number is not None and lot.cadastral_number != ""
            new_cadastral = None
            if not had_cadastral:
                parsed = parse_notice_detail(payload)
                new_cadastral = parsed.get("cadastral_number")
                if new_cadastral:
                    counts["cadastral_filled_now"] += 1
                else:
                    counts["cadastral_still_missing"] += 1
            else:
                parsed = parse_notice_detail(payload)
                counts["cadastral_already_set"] += 1

            new_municipality = parsed.get("municipality")
            new_settlement = parsed.get("settlement")
            new_permitted_use_codes_raw = parsed.get("permitted_use_codes")
            new_permitted_use_codes = (
                ", ".join(str(code) for code in new_permitted_use_codes_raw if code)
                if isinstance(new_permitted_use_codes_raw, list)
                else None
            )
            if new_municipality and not lot.municipality:
                counts["municipality_filled_now"] += 1
            if new_permitted_use_codes and not lot.permitted_use_codes:
                counts["permitted_use_codes_filled_now"] += 1

            changed = (
                (now_izhs != was_izhs)
                or (new_cadastral and not had_cadastral)
                or (new_municipality and not lot.municipality)
                or (new_permitted_use_codes and not lot.permitted_use_codes)
            )
            if changed:
                if len(sample_changes) < 25:
                    sample_changes.append(
                        {
                            "lot_id": lot.id,
                            "source_id": lot.source_id,
                            "title_short": (lot.title or "")[:80],
                            "is_izhs_candidate_before": was_izhs,
                            "is_izhs_candidate_after": now_izhs,
                            "cadastral_before": lot.cadastral_number,
                            "cadastral_after": new_cadastral or lot.cadastral_number,
                            "municipality_before": lot.municipality,
                            "municipality_after": new_municipality or lot.municipality,
                            "permitted_use_codes_before": lot.permitted_use_codes,
                            "permitted_use_codes_after": new_permitted_use_codes or lot.permitted_use_codes,
                        }
                    )
                if not dry_run:
                    lot.is_izhs_candidate = now_izhs
                    if new_cadastral and not had_cadastral:
                        lot.cadastral_number = new_cadastral
                    if new_municipality and not lot.municipality:
                        lot.municipality = new_municipality
                    if new_settlement and not lot.settlement:
                        lot.settlement = new_settlement
                    if new_permitted_use_codes and not lot.permitted_use_codes:
                        lot.permitted_use_codes = new_permitted_use_codes

        if not dry_run:
            db.commit()
    finally:
        db.close()

    return {
        "dry_run": dry_run,
        "izhs_keywords": keywords,
        "counts": counts,
        "sample_changes": sample_changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Офлайн-репроцессинг существующих Lot: пересчёт is_izhs_candidate и добор кадастра."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 = без ограничения")
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    report = reprocess(dry_run=args.dry_run, limit=args.limit or None)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = report["counts"]
    print("Offline lot reprocess report:")
    print(f"- mode: {'dry-run' if args.dry_run else 'apply'}")
    print(f"- keywords: {report['izhs_keywords']}")
    print(
        f"- lots: total={counts['lots_total']}, with_snapshot={counts['lots_with_snapshot']}, "
        f"without_snapshot={counts['lots_without_snapshot']}"
    )
    print(
        f"- IZHS: before={counts['izhs_before']} -> after={counts['izhs_after']} "
        f"(flipped_true={counts['izhs_flipped_true']}, flipped_false={counts['izhs_flipped_false']})"
    )
    print(
        f"- cadastral: already_set={counts['cadastral_already_set']}, "
        f"filled_now={counts['cadastral_filled_now']}, still_missing={counts['cadastral_still_missing']}"
    )
    print(
        f"- FIAS/codes: municipality_filled_now={counts['municipality_filled_now']}, "
        f"permitted_use_codes_filled_now={counts['permitted_use_codes_filled_now']}"
    )
    print(f"- output: {output_path}")


if __name__ == "__main__":
    main()

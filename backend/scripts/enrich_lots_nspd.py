"""Enrich existing lots from NSPD by cadastral number.

Use this after live ingest or demo import when the host can reach nspd.gov.ru.
It is intentionally separate from ingest so existing rows can be checked without
waiting for new Torgi files.

Examples:
    python scripts/enrich_lots_nspd.py --limit 50 --force
    python scripts/enrich_lots_nspd.py --limit 10 --dry-run --force
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

from app.config import settings
from app.database import SessionLocal
from app.models import Lot
from app.services.nspd.enrich import (
    apply_nspd_features_to_lot,
    fetch_nspd_features_sync,
    nspd_cache_is_fresh,
)

DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "nspd_enrich_report.json"


def _lot_sample(lot: Lot, features_count: int, error: str | None = None) -> dict[str, Any]:
    return {
        "lot_id": lot.id,
        "source_id": lot.source_id,
        "cadastral_number": lot.cadastral_number,
        "features_count": features_count,
        "nspd_specified_area_sqm": lot.nspd_specified_area_sqm,
        "nspd_cost_value": lot.nspd_cost_value,
        "nspd_readable_address": lot.nspd_readable_address,
        "nspd_centroid_latitude": lot.nspd_centroid_latitude,
        "nspd_centroid_longitude": lot.nspd_centroid_longitude,
        "nspd_card_id": lot.nspd_card_id,
        "nspd_card_type": lot.nspd_card_type,
        "error": error,
    }


def enrich_existing_lots(
    *,
    limit: int,
    dry_run: bool,
    include_fresh: bool,
    commit_every: int,
    region: str | None,
) -> dict[str, Any]:
    counts = {
        "selected": 0,
        "checked": 0,
        "matched": 0,
        "no_match": 0,
        "failed": 0,
        "skipped_fresh": 0,
    }
    samples: list[dict[str, Any]] = []

    db = SessionLocal()
    try:
        stmt = (
            select(Lot)
            .where(Lot.cadastral_number.is_not(None))
            .where(Lot.cadastral_number != "")
            .order_by(Lot.nspd_enriched_at.asc().nullsfirst(), Lot.id.asc())
        )
        if region:
            stmt = stmt.where(Lot.region == region)
        if limit > 0:
            stmt = stmt.limit(limit)
        lots = db.scalars(stmt).all()
        counts["selected"] = len(lots)

        pending = 0
        for lot in lots:
            if not include_fresh and nspd_cache_is_fresh(lot):
                counts["skipped_fresh"] += 1
                continue
            cad = (lot.cadastral_number or "").strip()
            counts["checked"] += 1
            try:
                features = fetch_nspd_features_sync(cad)
                apply_nspd_features_to_lot(lot, features)
            except Exception as exc:
                counts["failed"] += 1
                if len(samples) < 25:
                    samples.append(_lot_sample(lot, 0, error=f"{type(exc).__name__}: {exc}"))
                continue

            if features:
                counts["matched"] += 1
            else:
                counts["no_match"] += 1
            if len(samples) < 25:
                samples.append(_lot_sample(lot, len(features)))

            if not dry_run:
                db.add(lot)
                pending += 1
                if pending >= commit_every:
                    db.commit()
                    pending = 0

        if dry_run:
            db.rollback()
        elif pending:
            db.commit()
    finally:
        db.close()

    return {
        "dry_run": dry_run,
        "region": region,
        "nspd_base_url": settings.nspd_base_url,
        "nspd_geoportal_search_path": settings.nspd_geoportal_search_path,
        "nspd_geoportal_thematic_id": settings.nspd_geoportal_thematic_id,
        "counts": counts,
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich existing lots from NSPD by cadastral number.")
    parser.add_argument("--limit", type=int, default=50, help="0 = no limit")
    parser.add_argument("--dry-run", action="store_true", help="Fetch NSPD data but rollback DB writes")
    parser.add_argument("--include-fresh", action="store_true", help="Ignore NSPD_REFRESH_AFTER_DAYS cache")
    parser.add_argument("--region", default="", help="Optional region code filter, e.g. 72")
    parser.add_argument("--force", action="store_true", help="Run even when NSPD_ENABLED=false in .env")
    parser.add_argument("--commit-every", type=int, default=10)
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    if args.commit_every <= 0:
        parser.error("--commit-every must be positive")
    if not settings.nspd_enabled and not args.force:
        parser.error("NSPD_ENABLED=false. Set NSPD_ENABLED=true or pass --force for a manual one-off run.")
    if args.force:
        settings.nspd_enabled = True

    report = enrich_existing_lots(
        limit=args.limit,
        dry_run=args.dry_run,
        include_fresh=args.include_fresh,
        commit_every=args.commit_every,
        region=args.region.strip() or None,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = report["counts"]
    print("NSPD enrichment report:")
    print(f"- mode: {'dry-run' if args.dry_run else 'apply'}")
    if report["region"]:
        print(f"- region: {report['region']}")
    print(f"- selected={counts['selected']}, checked={counts['checked']}, skipped_fresh={counts['skipped_fresh']}")
    print(f"- matched={counts['matched']}, no_match={counts['no_match']}, failed={counts['failed']}")
    print(f"- output: {output_path}")


if __name__ == "__main__":
    main()

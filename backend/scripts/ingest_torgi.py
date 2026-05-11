"""MVP GIS ingest (mvp_gis_* tables). Example:

  python scripts/ingest_torgi.py --dry-run --limit 50
  python scripts/ingest_torgi.py --limit 20
  # One concrete data-*.json from meta (no INGEST_SOURCE_URL synthesis / no discovery plan):
  python scripts/ingest_torgi.py --dry-run --source-url "https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260509T0000-20260510T0000-structure-20240401.json" --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.services.mvp.pipeline import run_mvp_ingest  # noqa: E402


def _print_stats(stats: dict) -> None:
    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))


async def _run(dry_run: bool, limit: int | None, source_url: str | None) -> dict:
    db = SessionLocal()
    try:
        return await run_mvp_ingest(db, dry_run=dry_run, limit=limit, data_file_url=source_url)
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="MVP GIS Torgi ingest -> mvp_gis_* tables")
    p.add_argument("--dry-run", action="store_true", help="Classify and print stats without DB writes")
    p.add_argument("--limit", type=int, default=None, help="Max OpenData list rows to process")
    p.add_argument(
        "--source-url",
        type=str,
        default=None,
        metavar="URL",
        help="Fetch this data-*.json only (bypasses discovery; do not use INGEST_SOURCE_URL for the same purpose)",
    )
    args = p.parse_args()
    stats = asyncio.run(_run(args.dry_run, args.limit, args.source_url))
    _print_stats(stats)


if __name__ == "__main__":
    main()

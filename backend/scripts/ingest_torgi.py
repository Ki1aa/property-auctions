"""MVP GIS ingest (mvp_gis_* tables). Example:

  python scripts/ingest_torgi.py --dry-run --limit 50
  python scripts/ingest_torgi.py --limit 20
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


async def _run(dry_run: bool, limit: int | None) -> dict:
    db = SessionLocal()
    try:
        return await run_mvp_ingest(db, dry_run=dry_run, limit=limit)
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="MVP GIS Torgi ingest -> mvp_gis_* tables")
    p.add_argument("--dry-run", action="store_true", help="Classify and print stats without DB writes")
    p.add_argument("--limit", type=int, default=None, help="Max OpenData list rows to process")
    args = p.parse_args()
    stats = asyncio.run(_run(args.dry_run, args.limit))
    _print_stats(stats)


if __name__ == "__main__":
    main()

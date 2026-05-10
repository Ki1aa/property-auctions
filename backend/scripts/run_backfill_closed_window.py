"""Run ingest backfill for a closed date window (end date excludes today).

Example (last 7 full days ending yesterday):
    python scripts/run_backfill_closed_window.py --days 7
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill ingest for [end-days+1 .. end] where end defaults to yesterday.")
    parser.add_argument("--days", type=int, default=7, help="Length of window in days (>=1)")
    parser.add_argument("--dry-run-print-only", action="store_true", help="Print dates only, do not run ingest")
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days must be >= 1")

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)

    print(f"Backfill window (inclusive): {start.isoformat()} .. {end.isoformat()} (today excluded)")

    if args.dry_run_print_only:
        print("Dry run: not invoking ingest.")
        return

    os.environ["INGEST_MODE"] = "backfill"
    os.environ["BACKFILL_FROM"] = start.isoformat()
    os.environ["BACKFILL_TO"] = end.isoformat()

    from app.database import SessionLocal
    from app.services.ingest.service import run_ingest

    db = SessionLocal()
    try:
        result = asyncio.run(run_ingest(db, mode="backfill"))
    finally:
        db.close()

    print("Backfill completed:", result)


if __name__ == "__main__":
    main()

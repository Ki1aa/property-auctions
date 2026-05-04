from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ingest in backfill mode for a date range (YYYY-MM-DD).")
    parser.add_argument("--from-date", required=True, help="Backfill start date, e.g. 2026-04-01")
    parser.add_argument("--to-date", default="", help="Backfill end date, e.g. 2026-04-28")
    args = parser.parse_args()

    os.environ["INGEST_MODE"] = "backfill"
    os.environ["BACKFILL_FROM"] = args.from_date
    if args.to_date:
        os.environ["BACKFILL_TO"] = args.to_date

    from app.database import SessionLocal
    from app.services.ingest.service import run_ingest

    db = SessionLocal()
    try:
        result = asyncio.run(run_ingest(db, mode="backfill"))
    finally:
        db.close()

    print("Backfill completed:")
    print(result)


if __name__ == "__main__":
    main()

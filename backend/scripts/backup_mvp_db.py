"""Copy SQLite dev database to data/backups/ before MVP schema changes."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402


def main() -> None:
    url = (settings.database_url or "").lower()
    if "sqlite" not in url and "+sqlite" not in url:
        print("Skip backup: not a SQLite DATABASE_URL")
        return
    # sqlite+pysqlite:///../data/app.db
    db_path = ROOT / "data" / "app.db"
    if not db_path.is_file():
        print(f"No file at {db_path}, skip backup")
        return
    out_dir = ROOT / "data" / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = out_dir / f"app_{ts}.db"
    shutil.copy2(db_path, dest)
    print(f"Backed up to {dest}")


if __name__ == "__main__":
    main()

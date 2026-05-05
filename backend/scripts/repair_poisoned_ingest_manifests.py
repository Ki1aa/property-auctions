"""Delete ingest_manifest rows that incorrectly mark zero-record runs as processed.

Two flavours of poisoning are repaired:
1. Torgi error envelope: HTTP 200 with `{"error": "..."}` saved as processed/0
   (blocks re-fetch once the slice is finally published).
2. Live-list mismatch: row says processed/records_count=0, but the URL now
   returns a non-empty `listObjects` (the slice is online but ingest never
   replayed it because the manifest's sha256 still matches an earlier run).

Both cases are removed so the next ingest pass can refetch and reprocess.

Usage (from backend/):
  python scripts/repair_poisoned_ingest_manifests.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from sqlalchemy import create_engine, delete, select

from app.config import settings
from app.models import IngestManifest
from app.services.ingest.service import _is_torgi_opendata_error_envelope, _pick_items

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        rows = conn.execute(
            select(IngestManifest.id, IngestManifest.source_url).where(
                IngestManifest.status == "processed",
                IngestManifest.records_count == 0,
            )
        ).fetchall()

    if not rows:
        logger.info("No candidate manifests (processed, records_count=0).")
        return

    timeout = settings.ingest_timeout_seconds
    to_delete: list[int] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        for manifest_id, source_url in rows:
            try:
                response = await client.get(source_url)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skip id=%s: fetch failed: %s", manifest_id, exc)
                continue

            if _is_torgi_opendata_error_envelope(payload):
                logger.info("Delete id=%s (Torgi error envelope)", manifest_id)
                to_delete.append(manifest_id)
                continue

            items = _pick_items(payload)
            if items:
                logger.info(
                    "Delete id=%s (manifest says 0 records, but live URL returns %s items)",
                    manifest_id,
                    len(items),
                )
                to_delete.append(manifest_id)

    if not to_delete:
        logger.info("Nothing to delete after inspection.")
        return

    with engine.begin() as conn:
        conn.execute(delete(IngestManifest).where(IngestManifest.id.in_(to_delete)))
    logger.info("Deleted %s manifest row(s).", len(to_delete))


if __name__ == "__main__":
    asyncio.run(main())
